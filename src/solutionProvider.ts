import * as vscode from 'vscode';
import { TranslationResponse, Solution } from './apiClient';

export class SolutionProvider {
    async showSolution(response: TranslationResponse): Promise<void> {
        const panel = vscode.window.createWebviewPanel(
            'errorSolution',
            'AI Error Translation',
            vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );

        panel.webview.html = this.generateSolutionHTML(response);

        panel.webview.onDidReceiveMessage(
            async (message) => {
                switch (message.command) {
                    case 'applySolution':
                        await this.applySolution(message.solution);
                        break;
                    case 'copySolution':
                        await this.copySolution(message.code);
                        break;
                }
            }
        );
    }

    private generateSolutionHTML(response: TranslationResponse): string {
        const solutions = response.solutions.map((solution, index) => `
            <div class="solution" data-index="${index}">
                <div class="solution-header">
                    <h3>${solution.title}</h3>
                    <div class="confidence">Confidence: ${Math.round(solution.confidence * 100)}%</div>
                </div>
                <p class="solution-description">${solution.description}</p>
                ${solution.code ? `
                    <div class="code-block">
                        <pre><code>${this.escapeHtml(solution.code)}</code></pre>
                        <div class="code-actions">
                            <button onclick="applySolution(${index})">Apply Fix</button>
                            <button onclick="copySolution('${this.escapeHtml(solution.code)}')">Copy Code</button>
                        </div>
                    </div>
                ` : ''}
                ${solution.steps.length > 0 ? `
                    <div class="steps">
                        <h4>Steps:</h4>
                        <ol>
                            ${solution.steps.map(step => `<li>${step}</li>`).join('')}
                        </ol>
                    </div>
                ` : ''}
            </div>
        `).join('');

        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AI Error Translation</title>
                <style>
                    body {
                        font-family: var(--vscode-font-family);
                        font-size: var(--vscode-font-size);
                        color: var(--vscode-foreground);
                        background-color: var(--vscode-editor-background);
                        padding: 20px;
                        line-height: 1.6;
                    }
                    .header {
                        margin-bottom: 20px;
                        padding-bottom: 10px;
                        border-bottom: 1px solid var(--vscode-panel-border);
                    }
                    .error-type {
                        background-color: var(--vscode-badge-background);
                        color: var(--vscode-badge-foreground);
                        padding: 2px 8px;
                        border-radius: 3px;
                        font-size: 12px;
                        margin-left: 10px;
                    }
                    .explanation {
                        margin-bottom: 20px;
                        padding: 15px;
                        background-color: var(--vscode-textBlockQuote-background);
                        border-left: 4px solid var(--vscode-textBlockQuote-border);
                    }
                    .solution {
                        margin-bottom: 20px;
                        padding: 15px;
                        border: 1px solid var(--vscode-panel-border);
                        border-radius: 5px;
                        background-color: var(--vscode-editor-background);
                    }
                    .solution-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 10px;
                    }
                    .confidence {
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                    }
                    .code-block {
                        margin: 10px 0;
                        position: relative;
                    }
                    .code-block pre {
                        background-color: var(--vscode-textCodeBlock-background);
                        padding: 10px;
                        border-radius: 3px;
                        overflow-x: auto;
                        font-family: var(--vscode-editor-font-family);
                    }
                    .code-actions {
                        margin-top: 10px;
                    }
                    .code-actions button {
                        background-color: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        padding: 6px 12px;
                        margin-right: 10px;
                        border-radius: 3px;
                        cursor: pointer;
                        font-size: 12px;
                    }
                    .code-actions button:hover {
                        background-color: var(--vscode-button-hoverBackground);
                    }
                    .steps {
                        margin-top: 10px;
                    }
                    .steps ol {
                        padding-left: 20px;
                    }
                    .steps li {
                        margin-bottom: 5px;
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Error Translation Result</h1>
                    <span class="error-type">${response.errorType}</span>
                </div>
                
                <div class="explanation">
                    <h2>Explanation</h2>
                    <p>${response.explanation}</p>
                </div>
                
                <div class="solutions">
                    <h2>Solutions</h2>
                    ${solutions}
                </div>
                
                <script>
                    const vscode = acquireVsCodeApi();
                    
                    function applySolution(index) {
                        const solutions = ${JSON.stringify(response.solutions)};
                        vscode.postMessage({
                            command: 'applySolution',
                            solution: solutions[index]
                        });
                    }
                    
                    function copySolution(code) {
                        vscode.postMessage({
                            command: 'copySolution',
                            code: code
                        });
                    }
                </script>
            </body>
            </html>
        `;
    }

    private escapeHtml(text: string): string {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    private async applySolution(solution: Solution): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor to apply solution');
            return;
        }

        if (!solution.code) {
            vscode.window.showErrorMessage('No code to apply in this solution');
            return;
        }

        try {
            const document = editor.document;
            const selection = editor.selection;
            
            await editor.edit((editBuilder) => {
                if (solution.lineNumber !== undefined) {
                    const line = document.lineAt(solution.lineNumber);
                    editBuilder.replace(line.range, solution.code!);
                } else if (!selection.isEmpty) {
                    editBuilder.replace(selection, solution.code!);
                } else {
                    editBuilder.insert(editor.selection.active, solution.code!);
                }
            });

            vscode.window.showInformationMessage('Solution applied successfully!');
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to apply solution: ${error}`);
        }
    }

    private async copySolution(code: string): Promise<void> {
        try {
            await vscode.env.clipboard.writeText(code);
            vscode.window.showInformationMessage('Code copied to clipboard!');
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to copy code: ${error}`);
        }
    }
}
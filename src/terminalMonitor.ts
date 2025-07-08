import * as vscode from 'vscode';
import { ErrorTranslator } from './errorTranslator';

export class TerminalMonitor implements vscode.Disposable {
    private disposables: vscode.Disposable[] = [];
    private errorPatterns: RegExp[] = [
        /Error:/i,
        /Exception:/i,
        /Traceback/i,
        /TypeError:/i,
        /ReferenceError:/i,
        /SyntaxError:/i,
        /AttributeError:/i,
        /KeyError:/i,
        /ValueError:/i,
        /IndexError:/i,
        /Failed/i,
        /Fatal/i
    ];

    constructor(private errorTranslator: ErrorTranslator) {
        this.setupTerminalMonitoring();
    }

    private setupTerminalMonitoring(): void {
        const onDidOpenTerminal = vscode.window.onDidOpenTerminal((terminal) => {
            console.log(`Terminal opened: ${terminal.name}`);
        });

        const onDidCloseTerminal = vscode.window.onDidCloseTerminal((terminal) => {
            console.log(`Terminal closed: ${terminal.name}`);
        });

        const onDidChangeActiveTerminal = vscode.window.onDidChangeActiveTerminal((terminal) => {
            if (terminal) {
                console.log(`Active terminal changed: ${terminal.name}`);
            }
        });

        this.disposables.push(
            onDidOpenTerminal,
            onDidCloseTerminal,
            onDidChangeActiveTerminal
        );
    }

    private detectError(output: string): string | null {
        const lines = output.split('\n');
        
        for (const line of lines) {
            if (this.errorPatterns.some(pattern => pattern.test(line))) {
                return this.extractErrorContext(lines, lines.indexOf(line));
            }
        }
        
        return null;
    }

    private extractErrorContext(lines: string[], errorLineIndex: number): string {
        const contextLines = 5;
        const start = Math.max(0, errorLineIndex - contextLines);
        const end = Math.min(lines.length, errorLineIndex + contextLines + 1);
        
        return lines.slice(start, end).join('\n');
    }

    async handleDetectedError(errorText: string): Promise<void> {
        const config = vscode.workspace.getConfiguration('ai-error-translator');
        const autoCapture = config.get<boolean>('autoCapture', true);
        
        if (autoCapture) {
            const action = await vscode.window.showInformationMessage(
                'Error detected in terminal. Would you like to translate it?',
                'Translate',
                'Ignore'
            );
            
            if (action === 'Translate') {
                await this.errorTranslator.translateError(errorText);
            }
        }
    }

    dispose(): void {
        this.disposables.forEach(disposable => disposable.dispose());
    }
}
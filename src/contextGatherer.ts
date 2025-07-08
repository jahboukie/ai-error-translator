import * as vscode from 'vscode';
import * as path from 'path';

export interface ErrorContext {
    errorText: string;
    language: string;
    filePath?: string;
    lineNumber?: number;
    surroundingCode?: string;
    projectStructure?: string[];
    recentChanges?: string;
    dependencies?: any;
}

export class ContextGatherer {
    async gatherContext(errorText: string): Promise<ErrorContext> {
        const activeEditor = vscode.window.activeTextEditor;
        const context: ErrorContext = {
            errorText,
            language: activeEditor?.document.languageId || 'unknown'
        };

        if (activeEditor) {
            context.filePath = activeEditor.document.fileName;
            context.lineNumber = activeEditor.selection.active.line;
            context.surroundingCode = await this.getSurroundingCode(activeEditor);
        }

        context.projectStructure = await this.getProjectStructure();
        context.recentChanges = await this.getRecentGitChanges();
        context.dependencies = await this.getDependencies();

        return context;
    }

    private async getSurroundingCode(editor: vscode.TextEditor): Promise<string> {
        const document = editor.document;
        const currentLine = editor.selection.active.line;
        const maxLines = vscode.workspace.getConfiguration('ai-error-translator').get<number>('maxContextLines', 50);
        
        const startLine = Math.max(0, currentLine - Math.floor(maxLines / 2));
        const endLine = Math.min(document.lineCount - 1, currentLine + Math.floor(maxLines / 2));
        
        const range = new vscode.Range(startLine, 0, endLine, document.lineAt(endLine).text.length);
        return document.getText(range);
    }

    private async getProjectStructure(): Promise<string[]> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            return [];
        }

        const rootPath = workspaceFolders[0].uri.fsPath;
        const structure: string[] = [];

        try {
            const files = await vscode.workspace.findFiles(
                '**/*.{js,ts,py,java,cs,cpp,c,h,json,yaml,yml,md}',
                '**/node_modules/**',
                100
            );

            for (const file of files) {
                const relativePath = path.relative(rootPath, file.fsPath);
                structure.push(relativePath);
            }
        } catch (error) {
            console.error('Error gathering project structure:', error);
        }

        return structure;
    }

    private async getRecentGitChanges(): Promise<string> {
        try {
            const gitExtension = vscode.extensions.getExtension('vscode.git')?.exports;
            if (!gitExtension) {
                return '';
            }

            const api = gitExtension.getAPI(1);
            if (!api.repositories.length) {
                return '';
            }

            const repo = api.repositories[0];
            const changes = await repo.getDiff();
            return changes || '';
        } catch (error) {
            console.error('Error getting git changes:', error);
            return '';
        }
    }

    private async getDependencies(): Promise<any> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            return null;
        }

        const rootPath = workspaceFolders[0].uri.fsPath;
        const dependencies: any = {};

        try {
            const packageJsonUri = vscode.Uri.file(path.join(rootPath, 'package.json'));
            const packageJsonDoc = await vscode.workspace.openTextDocument(packageJsonUri);
            const packageJson = JSON.parse(packageJsonDoc.getText());
            dependencies.npm = {
                dependencies: packageJson.dependencies,
                devDependencies: packageJson.devDependencies
            };
        } catch (error) {
            // package.json not found or invalid
        }

        try {
            const requirementsUri = vscode.Uri.file(path.join(rootPath, 'requirements.txt'));
            const requirementsDoc = await vscode.workspace.openTextDocument(requirementsUri);
            dependencies.python = requirementsDoc.getText().split('\n').filter(line => line.trim());
        } catch (error) {
            // requirements.txt not found
        }

        return Object.keys(dependencies).length > 0 ? dependencies : null;
    }
}
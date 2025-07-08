import * as vscode from 'vscode';
import { ConfigManager } from './configManager';
import { ContextGatherer } from './contextGatherer';
import { ApiClient } from './apiClient';
import { SolutionProvider } from './solutionProvider';

export class ErrorTranslator {
    private contextGatherer: ContextGatherer;
    private apiClient: ApiClient;
    private solutionProvider: SolutionProvider;

    constructor(private configManager: ConfigManager) {
        this.contextGatherer = new ContextGatherer();
        this.apiClient = new ApiClient(configManager);
        this.solutionProvider = new SolutionProvider();
    }

    async translateError(errorText: string): Promise<void> {
        try {
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "Translating error...",
                cancellable: true
            }, async (progress, token) => {
                progress.report({ increment: 0, message: "Gathering context..." });
                
                const context = await this.contextGatherer.gatherContext(errorText);
                
                progress.report({ increment: 30, message: "Analyzing error..." });
                
                const solution = await this.apiClient.translateError(errorText, context);
                
                progress.report({ increment: 80, message: "Preparing solution..." });
                
                await this.solutionProvider.showSolution(solution);
                
                progress.report({ increment: 100, message: "Complete!" });
            });
        } catch (error) {
            vscode.window.showErrorMessage(`Error translation failed: ${error}`);
        }
    }

    async captureAndTranslateError(): Promise<void> {
        try {
            const capturedError = await this.captureLastError();
            if (capturedError) {
                await this.translateError(capturedError);
            } else {
                vscode.window.showWarningMessage('No recent error found. Try running your code first.');
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Error capture failed: ${error}`);
        }
    }

    private async captureLastError(): Promise<string | null> {
        const terminals = vscode.window.terminals;
        if (terminals.length === 0) {
            return null;
        }

        const activeTerminal = vscode.window.activeTerminal;
        if (!activeTerminal) {
            return null;
        }

        // For now, let's simulate terminal capture by asking user to copy error
        const result = await vscode.window.showInputBox({
            prompt: 'Paste the error from your terminal',
            placeHolder: 'e.g., TypeError: Cannot read property \'map\' of undefined',
            ignoreFocusOut: true,
            validateInput: (value) => {
                if (!value || value.trim().length === 0) {
                    return 'Please paste an error message';
                }
                // Check for common error patterns
                const errorPatterns = [
                    /error/i,
                    /exception/i,
                    /traceback/i,
                    /failed/i,
                    /cannot/i,
                    /undefined/i,
                    /null/i,
                    /syntax/i
                ];
                
                if (!errorPatterns.some(pattern => pattern.test(value))) {
                    return 'This doesn\'t look like an error message. Please paste an actual error.';
                }
                
                return null;
            }
        });

        return result || null;
    }
}
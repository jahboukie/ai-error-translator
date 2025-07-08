import * as vscode from 'vscode';
import { ErrorTranslator } from './errorTranslator';
import { TerminalMonitor } from './terminalMonitor';
import { ConfigManager } from './configManager';

let errorTranslator: ErrorTranslator;
let terminalMonitor: TerminalMonitor;

export function activate(context: vscode.ExtensionContext) {
    console.log('AI Error Translator is now active!');

    const configManager = new ConfigManager();
    errorTranslator = new ErrorTranslator(configManager);
    terminalMonitor = new TerminalMonitor(errorTranslator);

    const translateErrorCommand = vscode.commands.registerCommand(
        'ai-error-translator.translateError',
        async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showErrorMessage('No active editor found');
                return;
            }

            const selection = editor.selection;
            if (selection.isEmpty) {
                vscode.window.showErrorMessage('Please select the error text to translate');
                return;
            }

            const selectedText = editor.document.getText(selection);
            await errorTranslator.translateError(selectedText);
        }
    );

    const captureErrorCommand = vscode.commands.registerCommand(
        'ai-error-translator.captureError',
        async () => {
            await errorTranslator.captureAndTranslateError();
        }
    );

    const openSettingsCommand = vscode.commands.registerCommand(
        'ai-error-translator.openSettings',
        () => {
            vscode.commands.executeCommand('workbench.action.openSettings', 'ai-error-translator');
        }
    );

    context.subscriptions.push(
        translateErrorCommand,
        captureErrorCommand,
        openSettingsCommand,
        terminalMonitor
    );

    vscode.window.showInformationMessage('AI Error Translator is ready!');
}

export function deactivate() {
    if (terminalMonitor) {
        terminalMonitor.dispose();
    }
}
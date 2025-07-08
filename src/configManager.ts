import * as vscode from 'vscode';

export class ConfigManager {
    private readonly configSection = 'ai-error-translator';

    getApiKey(): string {
        return this.getConfig<string>('apiKey', '');
    }

    getApiEndpoint(): string {
        return this.getConfig<string>('apiEndpoint', 'https://api.ai-error-translator.com');
    }

    getAutoCapture(): boolean {
        return this.getConfig<boolean>('autoCapture', true);
    }

    getMaxContextLines(): number {
        return this.getConfig<number>('maxContextLines', 50);
    }

    getTelemetryEnabled(): boolean {
        return this.getConfig<boolean>('enableTelemetry', true);
    }

    async updateConfig(key: string, value: any): Promise<void> {
        const config = vscode.workspace.getConfiguration(this.configSection);
        await config.update(key, value, vscode.ConfigurationTarget.Global);
    }

    private getConfig<T>(key: string, defaultValue: T): T {
        const config = vscode.workspace.getConfiguration(this.configSection);
        return config.get<T>(key, defaultValue);
    }

    validateConfiguration(): boolean {
        const apiKey = this.getApiKey();
        const apiEndpoint = this.getApiEndpoint();

        if (!apiKey || apiKey.trim() === '') {
            vscode.window.showWarningMessage(
                'AI Error Translator: API key not configured. Please set your API key in settings.',
                'Open Settings'
            ).then(selection => {
                if (selection === 'Open Settings') {
                    vscode.commands.executeCommand('workbench.action.openSettings', 'ai-error-translator.apiKey');
                }
            });
            return false;
        }

        if (!apiEndpoint || apiEndpoint.trim() === '') {
            vscode.window.showWarningMessage('AI Error Translator: API endpoint not configured.');
            return false;
        }

        return true;
    }
}
import axios from 'axios';
import { ConfigManager } from './configManager';
import { ErrorContext } from './contextGatherer';

export interface TranslationRequest {
    errorText: string;
    context: ErrorContext;
}

export interface TranslationResponse {
    explanation: string;
    solutions: Solution[];
    confidence: number;
    errorType: string;
}

export interface Solution {
    title: string;
    description: string;
    code?: string;
    filePath?: string;
    lineNumber?: number;
    confidence: number;
    steps: string[];
}

export class ApiClient {
    private client: any;

    constructor(private configManager: ConfigManager) {
        this.client = axios.create({
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'ai-error-translator-vscode'
            }
        });

        this.setupInterceptors();
    }

    async translateError(errorText: string, context: ErrorContext): Promise<TranslationResponse> {
        if (!this.configManager.validateConfiguration()) {
            throw new Error('Configuration validation failed');
        }

        const request: TranslationRequest = {
            errorText,
            context
        };

        try {
            const response = await this.client.post(
                `${this.configManager.getApiEndpoint()}/translate`,
                request,
                {
                    headers: {
                        'Authorization': `Bearer ${this.configManager.getApiKey()}`
                    }
                }
            );

            return response.data;
        } catch (error: any) {
            if (error.response) {
                if (error.response.status === 401) {
                    throw new Error('Invalid API key. Please check your configuration.');
                } else if (error.response.status === 429) {
                    throw new Error('Rate limit exceeded. Please try again later.');
                } else if (error.response.status >= 500) {
                    throw new Error('Server error. Please try again later.');
                } else {
                    throw new Error(`API error: ${error.response.data?.message || error.message}`);
                }
            }
            throw new Error(`Network error: ${error.message || error}`);
        }
    }

    private setupInterceptors(): void {
        this.client.interceptors.request.use(
            (config: any) => {
                console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
                return config;
            },
            (error: any) => {
                console.error('API Request Error:', error);
                return Promise.reject(error);
            }
        );

        this.client.interceptors.response.use(
            (response: any) => {
                console.log(`API Response: ${response.status} ${response.statusText}`);
                return response;
            },
            (error: any) => {
                console.error('API Response Error:', error.response?.status, error.response?.statusText);
                return Promise.reject(error);
            }
        );
    }
}
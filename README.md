# AI Error Translator

A VS Code extension that instantly translates and fixes programming errors using AI. Perfect for developers who want to save time and AI assistant messages when debugging code.

## Features

- **Instant Error Translation**: Select error text to get AI-powered explanations and solutions
- **Smart Context Gathering**: Automatically includes relevant code context, file structure, and dependencies
- **One-Click Solutions**: Apply fixes directly to your code with a single click
- **Terminal Error Analysis**: Paste terminal errors for detailed analysis
- **Multi-Language Support**: Works with JavaScript, TypeScript, Python, Java, C#, and more

## Installation

1. Install the extension from the VS Code marketplace
2. Subscribe to a plan at [errortranslator.com](https://errortranslator.com) to get your API key
3. Configure your API key in settings (`Ctrl+,` → search "ai-error-translator")
4. Start translating errors with `Ctrl+Alt+E`

## Usage

### Translate Selected Error Text
1. Select the error text in your editor
2. Right-click and choose "Translate Error" or press `Ctrl+Alt+E`
3. View the AI-generated explanation and solutions

### Capture and Translate Errors
1. Press `Ctrl+Alt+E` without selecting text
2. Paste the error text when prompted
3. Get instant solutions with confidence ratings

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `ai-error-translator.apiKey` | Your API key from subscription | (empty) |
| `ai-error-translator.apiEndpoint` | Backend API endpoint | https://ai-error-translator-backend-196276076073.us-central1.run.app |
| `ai-error-translator.maxContextLines` | Maximum lines of context to include | 50 |
| `ai-error-translator.enableTelemetry` | Enable anonymous usage telemetry | true |

## Commands

- `AI Error Translator: Translate Error` - Translate selected error text
- `AI Error Translator: Capture & Translate Error` - Capture and translate last error
- `AI Error Translator: Open Settings` - Open extension settings

## Requirements

- VS Code 1.74.0 or higher
- Active internet connection
- Valid subscription (get one at [errortranslator.com](https://errortranslator.com))

## Development

### Building the Extension

```bash
npm install
npm run compile
```

### Testing

```bash
npm test
```

### Packaging

```bash
npm run package
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: support@errortranslator.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/ai-error-translator/issues)
- 🌐 Website: [errortranslator.com](https://errortranslator.com)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes.

---

**Happy debugging!** 🚀
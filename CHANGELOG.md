# Changelog

All notable changes to xgen-waveform-viewer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2024-12-20

### Added
- **Configuration Persistence**: User preferences are now saved and restored automatically
  - Serial port settings (last used port, baudrate, parity, etc.)
  - Display settings (X/Y axis ranges, buffer size, theme)
  - Recording settings (format, save directory)
  - Window geometry and size
- **Keyboard Shortcuts**: Quick access to common operations
  - `Space`: Resume auto-scroll (Follow)
  - `C`: Connect/Disconnect serial
  - `R`: Start/Stop recording
  - `F`: Fit all buffer data in view
  - `Y`: Toggle Y-axis auto/manual mode
  - `+/-`: Zoom in/out on X-axis
  - `Ctrl+S`: Save buffer to file
  - `Ctrl+E`: Export buffer as CSV
  - `Ctrl+Q`: Exit application
- **Theme Support**: Dark and Light theme options
  - Accessible via View > Theme menu
  - Themes persist across sessions
  - Dynamically updates UI colors and waveform display
- **Auto Reconnect**: Automatic reconnection when serial connection drops
  - Configurable via Connection > Auto Reconnect menu
  - Default reconnection delay: 3 seconds
  - Preserves last connection configuration
- **Menu Bar**: New menu system for better organization
  - File menu: Save, Export, Exit
  - View menu: Theme switcher, Follow, Show All
  - Connection menu: Connect/Disconnect, Auto Reconnect
  - Help menu: Keyboard Shortcuts, About
- **About Dialog**: Shows application version and license information

### Changed
- UI layout improvements for better organization
- Status bar now shows more detailed connection state
- Improved window state restoration
- Theme colors are now dynamically applied to waveform display

### Fixed
- Window size and position now properly saved and restored
- Settings are synchronized to disk on application exit

## [2.0.0] - 2024-11-15

### Added
- Initial release
- Real-time UART ADC waveform viewer
- CRC-16-CCITT frame validation
- Dynamic frame length support
- Auto resync and sequence number gap detection
- pyqtgraph real-time waveform display
- Data recording (BIN v2 and CSV formats)
- Flexible X/Y axis control
- Buffer management with configurable size
- GitHub Actions automated release workflow

[2.1.0]: https://github.com/X-Gen-Lab/xgen-waveform-viewer/compare/V2.0...V2.1
[2.0.0]: https://github.com/X-Gen-Lab/xgen-waveform-viewer/releases/tag/V2.0

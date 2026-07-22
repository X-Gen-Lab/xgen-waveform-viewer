# Changelog

All notable changes to xgen-waveform-viewer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2024-12-21

### Added
- **Measurement Tools**: Professional-grade waveform analysis capabilities
  - Draggable ruler for time interval and amplitude measurements
  - Automatic peak detection with visual markers (positive/negative peaks)
  - Real-time statistical calculations (Mean, RMS, Min, Max, Peak-to-Peak)
  - Frequency and period calculation based on peak intervals
  - Measurement results panel with organized display
  - New shortcuts: `M` (toggle ruler), `P` (detect peaks)
- **Trigger System**: Advanced signal capture functionality
  - Multiple trigger modes (Disabled, Auto, Normal, Single)
  - Multiple trigger types (Rising Edge, Falling Edge, Both Edges, Level High, Level Low)
  - Configurable threshold and hysteresis for noise immunity
  - Pre-trigger sample configuration
  - Real-time trigger status indication
  - Single-shot capture with arm/disarm control
  - New shortcut: `T` (arm single trigger)
- **Recording Enhancements**: Improved data capture workflow
  - Pause/Resume recording during capture (shortcut: `Ctrl+P`)
  - Auto-segmentation by duration or file size
  - Real-time recording preview (duration, file size, frame count, status)
  - Pause statistics (pause count, total pause duration)
  - Segment index tracking for multi-file recordings
  - Enhanced metadata with recording statistics
- **Side Panel UI**: New collapsible tool panel
  - Tabbed interface with "Measurement" and "Trigger" tabs
  - Adjustable width with splitter
  - Does not interfere with waveform display area

### Changed
- Updated version to V2.2.0
- Enhanced recorder module with pause/resume and segmentation support
- Improved status bar to show detailed recording information
- Main window now includes integrated measurement and trigger panels
- Recording statistics now include pause and segmentation information

### Technical Details
- New module: `measurement_tools.py` - Core measurement functionality
  - `Ruler` class: Draggable measurement ruler
  - `PeakMarker` class: Visual peak markers
  - `MeasurementPanel` class: Results display UI
  - `MeasurementEngine` class: Calculation algorithms
  - `MeasurementResult` dataclass: Structured results
- New module: `trigger.py` - Trigger detection system
  - `TriggerDetector` class: Real-time trigger detection
  - `TriggerPanel` class: Trigger control UI
  - `TriggerConfig` dataclass: Configuration management
  - `TriggerEvent` dataclass: Trigger event information
  - `TriggerMode` and `TriggerType` enums
- Enhanced `recorder.py`:
  - Added `pause()`, `resume()`, `is_paused()` methods
  - Added `get_preview()` for real-time statistics
  - Added auto-segmentation logic (`_should_create_segment()`, `_create_new_segment()`)
  - New control signals: `_PAUSE`, `_RESUME`
  - Enhanced `RecorderStats` with pause and segmentation fields

### API Changes
- `FrameRecorder.__init__()`: Added `auto_segment_duration` and `auto_segment_size` parameters
- `RecorderStats`: Added `paused`, `pause_count`, `total_pause_duration`, `file_size_bytes`, `segment_index` fields
- `RecorderStats`: Added `duration_display` and `file_size_display` properties for formatted output

### Configuration
New configuration keys:
- `measurement/ruler_enabled`: Enable ruler on startup
- `measurement/peak_threshold`: Peak detection threshold (0.0-1.0)
- `measurement/peak_min_distance`: Minimum distance between peaks (samples)
- `trigger/enabled`: Enable trigger on startup
- `trigger/mode`: Trigger mode (Disabled/Auto/Normal/Single)
- `trigger/type`: Trigger type
- `trigger/threshold`: Trigger threshold (ADC value)
- `trigger/hysteresis`: Hysteresis value
- `trigger/pre_trigger_samples`: Pre-trigger sample count
- `record/auto_segment_duration`: Auto-segment duration (seconds, 0=disabled)
- `record/auto_segment_size`: Auto-segment size (MB, 0=disabled)

### Performance
- Measurement updates optimized to 100ms refresh rate
- Peak detection uses vectorized operations for better performance
- Non-blocking file size queries for recording preview

### Documentation
- Added V2.2_INTEGRATION_GUIDE.md with detailed integration instructions
- Added RELEASE_NOTES_V2.2.md with comprehensive feature documentation
- Updated ROADMAP.md to mark V2.2 as completed

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

[2.2.0]: https://github.com/X-Gen-Lab/xgen-waveform-viewer/compare/V2.1...V2.2
[2.1.0]: https://github.com/X-Gen-Lab/xgen-waveform-viewer/compare/V2.0...V2.1
[2.0.0]: https://github.com/X-Gen-Lab/xgen-waveform-viewer/releases/tag/V2.0

# Changelog

All notable changes to xgen-waveform-viewer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-07-22

### Added - Multi-Channel Support 🎉
- **Multi-Channel Data Model**: Complete rewrite to support up to 16 independent ADC channels
  - `MultiChannelManager` class for channel lifecycle management
  - `ChannelConfig` dataclass for per-channel configuration
  - `ChannelData` dataclass for per-channel buffering
  - Independent sample buffers, timestamps, and sequence tracking per channel
  - Automatic color assignment from predefined palette
- **Channel Management UI**: Professional channel configuration panel
  - Visual channel list with editable labels, colors, and visibility
  - Channel grouping for logical organization
  - Per-channel Y-axis offset and scaling
  - Real-time channel statistics display
  - Configuration save/load with JSON serialization
- **Multi-Channel Display**: Enhanced visualization
  - Overlay mode: All channels on same Y-axis
  - Stacked mode: Separate Y-axis regions per channel
  - Configurable channel colors for easy identification
  - Show/hide channels without data loss
  - Per-channel memory management with configurable limits

### Added - Protocol Extension Framework 🔧
- **Protocol Parser Architecture**: Flexible protocol handling system
  - Abstract `ProtocolParser` base class
  - `ProtocolFactory` for dynamic parser creation
  - Support for Binary V2 (default), Binary Custom, and ASCII protocols
  - Plugin-style protocol loading from JSON configuration files
- **Binary Custom Protocol**: User-defined binary frame formats
  - `FrameFormat` dataclass for complete frame specification
  - Configurable sync bytes, metadata layout, CRC parameters
  - Support for multiple endianness (little/big)
  - Optional sequence numbers and channel IDs
  - Variable sample sizes (1, 2, 4 bytes)
  - Maximum 4096 samples per frame
- **ASCII Text Protocol**: Human-readable data support
  - CSV format with configurable delimiters
  - Optional channel prefix (e.g., `#CH0:1234,5678`)
  - Multiple line terminator support (LF, CRLF, CR)
  - Automatic integer/float parsing
  - Ideal for debugging and simple devices
- **Protocol Configuration UI**: Visual protocol editor
  - Tab-based interface for different protocol types
  - Real-time parameter validation
  - Import/export protocol configurations as JSON
  - Protocol switching without code changes
  - Built-in examples and templates

### Added - Firmware Configuration & OTA 🚀
- **Firmware Version Management**: Comprehensive version tracking
  - `FirmwareVersion` dataclass with semantic versioning
  - Git commit hash and build date tracking
  - Version compatibility checking
  - Automatic upgrade recommendations
- **Firmware Configuration**: Remote parameter management
  - Sampling rate configuration (100 Hz - 1 MHz)
  - Frame length adjustment (1 - 4096 samples)
  - Multi-channel configuration (up to 16 channels)
  - Channel mask for selective channel enabling
  - ADC resolution and reference voltage settings
  - Hardware trigger configuration (level, edge, enable)
- **Firmware Command Protocol**: Bidirectional communication
  - Custom command frame format (0xFC 0xCF sync)
  - CRC-16 validation for command integrity
  - 14 command types including version query, config set/get, OTA
  - Response handling with timeout management
  - Structured error reporting
- **OTA Firmware Update**: Safe over-the-air updates
  - Chunked firmware transmission (256-byte blocks)
  - Real-time progress reporting
  - Automatic firmware verification
  - Update failure recovery with rollback
  - Bootloader entry support
  - Warning dialogs for safety
- **Firmware Configuration UI**: User-friendly management panel
  - Version information display with details
  - Configuration parameter editor
  - One-click firmware file selection
  - Progress bar for OTA updates
  - Operation log viewer
  - Device reset and bootloader controls

### Changed
- **Version**: Updated to V3.0.0 (major milestone release)
- **Architecture**: Refactored core data flow to support multi-channel
- **API**: Extended APIs to accept channel_id parameters
- **Dependencies**: No new required dependencies (all features in core)
- **Configuration**: Extended settings with multi-channel and protocol sections
- **Documentation**: Comprehensive V3.0 release notes and quick start guide

### Technical Details - New Modules
- **`multi_channel.py`**: Multi-channel data management (455 lines)
  - `ChannelConfig`: Channel metadata and display properties
  - `ChannelData`: Per-channel sample buffer with timestamps
  - `MultiChannelManager`: Channel lifecycle and configuration management
- **`protocol.py`**: Protocol parsing framework (570 lines)
  - `ProtocolParser`: Abstract base class for parsers
  - `BinaryV2Parser`: Default protocol (backward compatible)
  - `CustomBinaryParser`: User-defined binary protocols
  - `ASCIIParser`: Text-based protocol support
  - `ProtocolFactory`: Parser instantiation and configuration
  - `FrameFormat`: Binary frame specification
  - `ParsedFrame`: Unified parsing result
- **`firmware_config.py`**: Firmware management (450 lines)
  - `FirmwareConfigManager`: Command interface to firmware
  - `FirmwareVersion`: Version information structure
  - `FirmwareConfig`: Complete configuration parameters
  - `FirmwareCommandType`: Command enumeration
  - `check_firmware_compatibility()`: Version validation
- **`channel_panel.py`**: Channel management UI (280 lines)
  - `ChannelPanel`: Main channel list and controls
  - `ColorButton`: Custom color picker widget
- **`protocol_config_panel.py`**: Protocol configuration UI (350 lines)
  - `ProtocolConfigPanel`: Multi-tab protocol editor
  - Protocol-specific configuration forms
  - Import/export functionality
- **`firmware_panel.py`**: Firmware management UI (400 lines)
  - `FirmwarePanel`: Version, config, and OTA interface
  - Real-time progress tracking
  - Operation logging display

### API Changes
- **Multi-Channel APIs**:
  - `MultiChannelManager.add_channel(channel_id, label, color)`: Create channel
  - `MultiChannelManager.append_data(channel_id, samples, seq, timestamp)`: Add data
  - `MultiChannelManager.get_channel_config(channel_id)`: Query configuration
  - `MultiChannelManager.update_channel_config(channel_id, **kwargs)`: Modify settings
  - `MultiChannelManager.save_config()` / `load_config()`: Persistence
- **Protocol APIs**:
  - `ProtocolFactory.create_parser(protocol_type, config)`: Create parser
  - `ProtocolFactory.load_from_file(filepath)`: Load from JSON
  - `ProtocolParser.parse_frame(data)`: Parse single frame
  - `ProtocolParser.find_sync(buffer)`: Locate sync header
  - `ProtocolParser.validate_frame(data)`: Check integrity
- **Firmware APIs**:
  - `FirmwareConfigManager.get_firmware_version()`: Query version
  - `FirmwareConfigManager.get/set_firmware_config()`: Config operations
  - `FirmwareConfigManager.set_sample_rate(rate)`: Configure sampling
  - `FirmwareConfigManager.ota_update(firmware_data)`: Update firmware
  - Signal-based response handling (async pattern)

### Configuration
New configuration sections and keys:
- `multi_channel/*`: Channel definitions and display settings
- `protocol/type`: Active protocol type
- `protocol/custom_config`: Custom protocol parameters
- `firmware/min_version`: Minimum compatible firmware version
- `firmware/check_on_connect`: Auto version check
- `ota/chunk_size`: OTA transfer chunk size
- `ota/verify_on_complete`: Post-update verification

### Documentation & Examples 📚
- **Release Notes**: Comprehensive V3.0 feature documentation (1500+ lines)
- **Quick Start Guide**: Step-by-step tutorials for new features
- **Example Scripts**:
  - `v3.0_multi_channel_example.py`: Multi-channel demo with 4 simulated channels
  - `v3.0_custom_protocol_example.py`: Protocol configuration examples
  - `v3.0_firmware_config_example.py`: Firmware management examples
- **Protocol Templates**: Ready-to-use JSON configurations
  - `binary_custom_example.json`: Multi-channel custom binary
  - `ascii_example.json`: CSV and prefixed text protocols
  - `modbus_rtu_example.json`: Modbus-style protocol template

### Backward Compatibility ✅
- **Binary V2 Protocol**: Remains the default, fully compatible
- **Single Channel Mode**: Works as before (channel 0)
- **Existing Recordings**: Can still be loaded and played back
- **Configuration Migration**: Automatic upgrade from V2.x settings
- **Firmware Interop**: V3.0 software works with V2.x firmware (limited features)

### Performance Optimizations ⚡
- **Per-Channel Buffering**: Reduced memory fragmentation
- **Lazy Rendering**: Only visible channels are drawn
- **Protocol Dispatch**: Zero-copy parsing where possible
- **Firmware Commands**: Async with 2-second timeout
- **OTA Throughput**: Optimized for high baud rates (921600+)

### Known Limitations ⚠️
- Maximum 16 channels (hardware/display constraint)
- OTA update requires continuous connection (no resume)
- TCP/UDP data sources not yet implemented (planned V3.1)
- Firmware config requires V3.0+ firmware

### Migration Guide
For users upgrading from V2.x:
1. **Settings**: Backup `~/.xgen-waveform-viewer/` before upgrade
2. **Firmware**: Update to V3.0 firmware for full feature access
3. **Protocols**: Default Binary V2 continues to work
4. **Channels**: Single-channel mode is automatic (no action needed)
5. **Recordings**: Old files remain compatible

### Security Notes 🔒
- OTA firmware is not encrypted (use trusted sources only)
- Firmware commands use CRC-16 (not cryptographically secure)
- Configuration files are plain JSON (sensitive data may be visible)
- Serial connection has no authentication

---

## [2.4.1] - 2025-01-22

### Fixed - UX Completeness
- **Playback Panel**: Enhanced signal connections and state management
  - Added pause/resume event handlers
  - Implemented proper serial control disabling during playback
  - Fixed control restoration after playback stops
  - Improved file loaded notification with detailed information
- **Export Functions**: Comprehensive error handling and user feedback
  - Added optional dependency checker with installation guidance
  - Implemented data validation before export
  - Added progress indication for large file exports
  - Enhanced error messages with actionable solutions
  - PNG/SVG: Pre-export data check, file size display
  - MATLAB: scipy dependency check, detailed export info
  - HDF5: h5py dependency check, compression ratio display, progress dialog
  - HTML Report: Option to open in browser after generation
- **Measurement Tools UI Integration**: Full accessibility
  - Added tool dock panel with Measurement and Trigger tabs
  - Implemented ruler shortcut (`M`) - toggle draggable measurement ruler
  - Implemented peak detection shortcut (`P`) - auto-detect and mark peaks
  - Connected measurement panel to update with results
  - Added View menu item and `Ctrl+T` shortcut for tool panel
- **Statistics Panel Access**: Easy discoverability
  - Added View menu item "Statistics Panel"
  - Added `Ctrl+I` shortcut
  - Connected live data updates from serial reader

### Added - Convenience Features
- **Quick Playback After Recording**: Seamless workflow
  - Prompt to playback immediately after recording completes
  - Auto-open playback panel and load file
  - Records metadata (frames, samples, duration) displayed
- **Smart Dependency Management**: Better user experience
  - Friendly dialog when optional packages missing
  - Direct link to installation documentation
  - Clear installation instructions (pip commands)
- **Enhanced Status Feedback**: Real-time operation visibility
  - All export operations show status in status bar
  - Progress indication for long operations
  - Clear mode indication (Live/Playback)
  
### Changed
- Updated version to V2.4.1
- Enhanced all export methods with try-catch error handling
- Improved user notification messages with more context
- Tool panel now hidden by default to save space

### Technical Details
- New methods in `MainWindow`:
  - `_setup_tool_panels()`: Initialize tool dock with tabs
  - `_check_optional_dependency()`: Unified dependency checker
  - `_toggle_ruler()`: Ruler display toggle with auto-panel-show
  - `_detect_peaks()`: Peak detection with configurable params
  - `_on_ruler_measurement_changed()`: Ruler result callback
  - `_on_trigger_config_changed()`: Trigger config callback
  - `_show_statistics_panel()`: Statistics panel launcher
  - `_load_playback_file()`: Auto-load playback file helper
  - `_on_playback_paused()`: Playback pause event
  - `_on_playback_resumed()`: Playback resume event
- Enhanced shortcuts:
  - `M`: Toggle ruler measurement tool
  - `P`: Detect and mark peaks
  - `Ctrl+T`: Toggle tool panel visibility
  - `Ctrl+I`: Open statistics panel
- Enhanced menu items:
  - View > Tool Panel (Measurement & Trigger)
  - View > Statistics Panel

### Developer Notes
- All new code includes comprehensive error handling
- Logging added for all major operations
- Status bar updates for better user feedback
- No performance regression
- Memory usage remains stable

## [2.4.0] - 2025-01-XX

### Added - Data Playback
- **Playback Engine**: Complete data replay system
  - Support for BIN and CSV format playback
  - Variable playback speed (0.1x ~ 10x adjustable)
  - Play/Pause/Stop/Resume controls
  - Visual progress bar with time display
  - Independent playback control panel
  - Accurate timing control with speed adjustment
- **Playback UI**: Dedicated playback control panel
  - File selection dialog with format filtering
  - Speed selector with preset speeds
  - Progress slider for visual feedback
  - File information display (format, sample rate, duration, etc.)
  - Keyboard shortcut: `Ctrl+P` to open playback panel
- **Playback Modes**: Seamless integration with main window
  - Automatic switching between live and playback modes
  - Disables serial connection during playback
  - Uses same waveform display as live acquisition
  - Maintains all viewing controls (zoom, pan, measurements)

### Added - Advanced Export Options
- **Image Export**: High-quality waveform image generation
  - PNG export with configurable resolution (default: 1920x1080)
  - SVG vector export for publication-quality graphics
  - Exports current visible waveform region
  - Accessible via File > Export As menu
- **MATLAB Format (.mat)**: Scientific computing integration
  - Exports samples, time array, and sample rate
  - Includes metadata and export timestamp
  - Compatible with MATLAB/Octave
  - Requires optional `scipy` package
  - Simple to load: `data = load('file.mat')`
- **HDF5 Format (.h5)**: High-efficiency data storage
  - Compressed storage using gzip (level 9)
  - Typical compression ratio: 50-70% space savings
  - Preserves all metadata and attributes
  - Standard format for scientific data
  - Requires optional `h5py` package
  - Supports very large datasets efficiently
- **HTML Statistics Report**: Professional documentation
  - Automatically generated HTML report with statistics
  - Includes waveform preview image
  - Displays comprehensive statistics (mean, RMS, peak-to-peak, etc.)
  - Frequency domain analysis (if applicable)
  - Data quality metrics (CRC errors, gaps, etc.)
  - Beautiful, print-friendly styling
  - Suitable for archiving and sharing

### Added - Waveform Comparison
- **Comparison Tool**: Statistical waveform analysis
  - Compare two waveforms side-by-side
  - Statistical metrics: mean, std, min, max
  - Difference calculations: MSE, MAE, max difference
  - Correlation coefficient
  - Programmatic API in `exporter.py`

### Changed
- Updated version to V2.4.0
- Enhanced main window with playback and export menus
- Added PyQt6-SVG dependency for SVG export support
- Improved file menu organization with export submenu
- Extended `pyproject.toml` with optional dependencies

### Technical Details - New Modules
- **`playback.py`**: Playback engine core
  - `PlaybackReader` class: Thread-based playback engine
  - `PlaybackInfo` dataclass: File and playback information
  - `PlaybackState` type: State enumeration (stopped/playing/paused)
  - Supports BIN and CSV format parsing
  - Accurate timing with speed control
  - Progress tracking and reporting
- **`playback_panel.py`**: Playback control UI
  - `PlaybackPanel` class: Qt widget for playback control
  - File selection and loading
  - Speed control with presets
  - Progress visualization
  - Play/Pause/Stop controls
  - Time formatting utilities
- **`exporter.py`**: Unified export functionality
  - `WaveformExporter` class: All export methods
  - `export_image_png()`: PNG image export
  - `export_image_svg()`: SVG vector export
  - `export_matlab()`: MATLAB format export
  - `export_hdf5()`: HDF5 format export with compression
  - `load_hdf5()`: HDF5 file loading
  - `export_statistics_html()`: HTML report generation
  - `export_statistics_json()`: JSON statistics export
  - `WaveformComparator` class: Waveform comparison tools

### API Changes
- Main window methods:
  - `_show_playback_panel()`: Open playback control panel
  - `_export_png()`: Export waveform as PNG
  - `_export_svg()`: Export waveform as SVG
  - `_export_matlab()`: Export data as MATLAB format
  - `_export_hdf5()`: Export data as HDF5 format
  - `_export_report_html()`: Generate HTML report
- Playback panel signals:
  - `file_loaded`: Emitted when file is loaded
  - `playback_started`: Emitted when playback starts
  - `playback_paused`: Emitted when playback pauses
  - `playback_resumed`: Emitted when playback resumes
  - `playback_stopped`: Emitted when playback stops

### Dependencies
- **Required**: Added `PyQt6-SVG>=6.4.0` for SVG export
- **Optional**: 
  - `scipy>=1.10.0` for MATLAB format export
  - `h5py>=3.8.0` for HDF5 format support
- Install full features: `pip install "xgen-waveform-viewer[full]"`

### Configuration
New menu items:
- File > Export As > Export as PNG...
- File > Export As > Export as SVG...
- File > Export As > Export as MATLAB (.mat)...
- File > Export As > Export as HDF5 (.h5)...
- File > Export As > Export Report (HTML)...
- File > Playback Recording... (Ctrl+P)

### Performance
- Playback engine optimized for large files
- HDF5 compression typically saves 50-70% disk space
- PNG export renders at full resolution (1920x1080)
- SVG export creates resolution-independent graphics
- HTML reports are lightweight and fast to generate

### Documentation
- Added `RELEASE_NOTES_V2.4.md` with comprehensive feature guide
- Added `examples/v2.4_playback_and_export_example.py` with usage examples
- Updated README.md with V2.4 features
- Updated ROADMAP.md to mark V2.4 as completed

### Known Limitations
- Playback of very large files (>100MB) may use significant memory
- PNG/SVG export captures only current visible region
- MATLAB and HDF5 export require optional dependencies
- Playback timing may vary slightly at extreme speeds (>5x)

## [2.3.0] - 2024-12-22

### Added - Performance Optimization
- **Min/Max Downsampling Algorithm**: Intelligent downsampling for high-density waveforms
  - Automatically activates when data points exceed threshold (default: 10,000 points)
  - Preserves waveform peaks and valleys using min/max segmentation
  - Configurable downsample threshold and target render points
  - Maintains visual fidelity while improving rendering performance
- **Frame Rate Limiting**: Configurable display refresh rate control
  - Adjustable FPS limit (1-120 FPS, default: 30 FPS)
  - Reduces CPU usage during high-speed data acquisition
  - Independent from data acquisition rate
- **Memory Management**: Automatic memory optimization for large datasets
  - Configurable memory limit (default: 200 MB)
  - Automatic buffer size adjustment based on memory constraints
  - Memory usage estimation and monitoring
  - Prevents system memory exhaustion during long captures

### Added - Robustness Improvements
- **Logging System**: Comprehensive event and error logging
  - Structured logging with categories (serial, frame, crc_error, seq_gap, resync, recording, performance)
  - Automatic log rotation (7-day retention)
  - Log file location: `~/.xgen-waveform-viewer/logs/`
  - Export logs to JSON for analysis
  - Separate log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Statistics Panel**: Real-time data integrity visualization
  - Live statistics: total frames, samples, CRC errors, sequence gaps, resyncs
  - Error rate calculation and trending
  - Time-series charts for FPS, error rate, and sample rate
  - Historical data retention (60 seconds)
  - Export statistics and logs
  - Reset statistics on demand
- **Enhanced Error Recovery**: Improved CRC and synchronization handling
  - Detailed logging of CRC validation failures
  - Sequence gap detection with gap size calculation
  - Resynchronization event tracking with reason codes
  - Short frame detection and recovery

### Changed
- Updated version to V2.3.0
- Enhanced `WaveformWidget` with performance optimizer integration
- Updated `SerialReader` with comprehensive event logging
- Improved error messages with structured details
- Optimized plot refresh timing based on FPS limit

### Technical Details - New Modules
- **`performance.py`**: Performance optimization engine
  - `PerformanceOptimizer` class: Downsampling and refresh rate control
  - `MemoryOptimizer` class: Memory limit enforcement
  - `DownsampleResult` dataclass: Downsampling metadata
  - `downsample_minmax()`: Min/max downsampling algorithm
  - `prepare_render_data()`: Render data preparation with automatic downsampling
- **`logger.py`**: Logging infrastructure
  - `AppLogger` class: Main logging interface
  - `LogEvent` dataclass: Structured event representation
  - Category-specific logging methods
  - JSON export functionality
  - Automatic log cleanup
- **`statistics_panel.py`**: Statistics visualization UI
  - `StatisticsPanel` class: Real-time statistics display
  - Three live charts: FPS, Error Rate, Sample Rate
  - Formatted statistics with color-coded warnings
  - Export and reset capabilities

### API Changes
- `WaveformWidget.set_performance_optimizer()`: Set performance optimizer instance
- `WaveformWidget.enable_downsampling()`: Enable/disable downsampling
- `WaveformWidget.is_downsampling_enabled()`: Query downsampling state
- `PerformanceOptimizer.set_fps_limit()`: Configure frame rate limit
- `PerformanceOptimizer.set_downsample_threshold()`: Configure downsample trigger
- `MemoryOptimizer.set_memory_limit_mb()`: Configure memory limit
- `AppLogger.log_*()`: Category-specific logging methods

### Configuration
New configuration keys:
- `performance/fps_limit`: Frame rate limit (FPS, default: 30)
- `performance/downsample_enabled`: Enable automatic downsampling (default: true)
- `performance/downsample_threshold`: Points threshold for downsampling (default: 10000)
- `performance/memory_limit_mb`: Memory limit in megabytes (default: 200)
- `logging/retention_days`: Log file retention period (default: 7)

### Performance Improvements
- 5-10x faster rendering for datasets > 10,000 points
- Reduced CPU usage by 30-50% with FPS limiting
- Eliminated frame drops during high-speed acquisition (>10 kHz)
- Memory usage capped at configured limit
- Smooth UI interaction even with large buffers (>10M samples)

### Documentation
- Added performance optimization guidelines
- Added logging system documentation
- Added troubleshooting guide for data integrity issues
- Updated ROADMAP.md to mark V2.3 as completed

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

# qbit2track - Project Agents & Guidelines

## 📋 Project Overview

**qbit2track** is a comprehensive Python application for automated torrent management, integrating with qBittorrent, TMDB, and various private trackers.

---

## 🤖 Development Agents

### Benjamin SCHWALD
**Role**: Lead Developer & Architect  
**Focus**: Core functionality, TMDB integration, filename analysis  
**Email**: b.schwald@majyx.net

### Assistant (Cascade)
**Role**: AI Pair Programming Assistant  
**Focus**: Code implementation, debugging, feature development  
**Expertise**: Python, API integration, regex patterns, file handling

---

## 🎯 Project Architecture

### Core Components
- **Extractor**: Torrent metadata extraction from qBittorrent
- **Filename Analyzer**: Pattern-based title and technical info extraction  
- **TMDB Matcher**: Movie/TV show matching with caching and retry logic
- **Uploader**: Multi-tracker upload with metadata mapping
- **CLI**: Command-line interface with progress tracking

### Key Design Principles
- **Modular**: Each component is independent and testable
- **Configurable**: YAML-based configuration with environment overrides
- **Resilient**: Retry mechanisms, error handling, graceful degradation
- **Performant**: Caching, batch processing, async operations where beneficial

---

## 📝 Development Guidelines

### Code Style
- **Python 3.11+**: Modern Python features and type hints
- **Type Hints**: All public APIs should have proper typing
- **Docstrings**: Google-style docstrings for all public methods
- **Logging**: Structured logging with appropriate levels (DEBUG, INFO, WARNING, ERROR)

### File Organization
```
qbit2track/
├── cli.py              # Command-line interface
├── config.py            # Configuration management
├── extractor.py          # qBittorrent integration
├── media/               # Media processing modules
│   ├── filename_analyzer.py
│   ├── tmdb_matcher.py
│   └── file_analyzer.py
├── models.py            # Data structures
├── uploader.py          # Multi-tracker uploads
├── utils.py             # Utilities and helpers
└── trackers/            # Tracker implementations
    └── lacale.py
```

### Configuration Management
- **Primary**: `config/config.yaml`
- **API Keys**: `config/api_config.yaml` (gitignored)
- **Examples**: Complete examples in `config/`
- **Validation**: Config validation on startup

---

## 🔧 Technical Decisions & Rationale

### TMDB Integration
- **Retry Mechanism**: Progressive title shortening (60% threshold)
- **Caching**: JSON-based cache with configurable expiry
- **Scoring**: Multi-factor scoring (exact match, substring, fuzzy)
- **Fallback**: Best result kept even if below threshold

### Filename Analysis
- **Accent Normalization**: Unicode NFD normalization for international content
- **Pattern Matching**: Regex-based extraction with progressive refinement
- **Title Cleaning**: Selective pattern removal, not aggressive truncation
- **Language Detection**: Pattern-based with multi-language support

### NFO Generation
- **pymediainfo Integration**: Detailed media file analysis
- **Technical Specs**: Container, codec, bitrate, resolution details
- **Audio Details**: Channels, sampling rate, language information
- **Subtitle Support**: Track parsing and language detection
- **Fallback Handling**: Graceful degradation when pymediainfo unavailable

---

## 🚀 Current Features

### ✅ Implemented
- [x] **qBittorrent Integration**: Complete torrent management
- [x] **TMDB Matching**: Advanced matching with retry mechanism
- [x] **Filename Analysis**: Accent normalization and pattern extraction
- [x] **Multi-tracker Support**: La Cale integration with metadata mapping
- [x] **CLI Interface**: Extract, upload, info, cache commands
- [x] **Configuration**: YAML-based with validation
- [x] **Caching**: TMDB and metadata caching
- [x] **Progress Tracking**: Progress bars and detailed logging
- [x] **Error Handling**: Graceful degradation and retry logic
- [x] **Enhanced NFO Generation**: pymediainfo integration for detailed technical specs

### 🚧 In Progress
- [ ] **Additional Trackers**: More private tracker implementations
- [ ] **Advanced Matching**: Machine learning for title matching
- [ ] **Batch Operations**: Bulk upload and management
- [ ] **Web Interface**: Optional web dashboard
- [ ] **Database Integration**: SQLite for metadata persistence
- [ ] **Testing Suite**: Comprehensive unit and integration tests

### 📋 Planned
- [ ] **Configuration UI**: Web-based configuration management
- [ ] **API Rate Limiting**: Intelligent rate limiting for TMDB
- [ ] **File Validation**: Media file integrity checking
- [ ] **Notification System**: Upload status notifications
- [ ] **Backup System**: Configuration and metadata backup

---

## 🐛 Known Issues & Solutions

### TMDB Rate Limiting
**Issue**: TMDB API rate limits during bulk operations  
**Solution**: Exponential backoff, caching, request batching

### Complex Filenames
**Issue**: International characters, inconsistent naming patterns  
**Solution**: Unicode normalization, progressive pattern matching, retry mechanism

### Tracker API Changes
**Issue**: Private trackers frequently change APIs  
**Solution**: Modular tracker architecture, configuration-driven mapping

### Memory Usage
**Issue**: Large torrent metadata processing  
**Solution**: Streaming processing, memory-efficient data structures

---

## 🔄 Maintenance Guidelines

### Regular Tasks
- **Dependency Updates**: Keep dependencies current and secure
- **Cache Cleanup**: Remove expired cache entries periodically
- **Log Rotation**: Implement log file rotation
- **Performance Monitoring**: Track processing times and success rates

### Code Quality
- **Type Coverage**: Aim for 100% type hint coverage
- **Test Coverage**: Maintain comprehensive test suite
- **Documentation**: Keep README and code docs current
- **Security**: Regular dependency audits and API key rotation

### Release Process
1. **Feature Complete**: All functionality working and tested
2. **Documentation Updated**: README, changelog, examples
3. **Version Bump**: Semantic versioning (MAJOR.MINOR.PATCH)
4. **Tag Created**: Git tag with version number
5. **Release Published**: GitHub release with notes

---

## 📊 Performance Metrics

### Success Criteria
- **TMDB Match Rate**: >85% for well-known content
- **Upload Success Rate**: >95% for configured trackers
- **Processing Speed**: <2s per torrent for metadata extraction
- **Memory Usage**: <500MB for typical operations
- **Error Rate**: <5% for normal operations

### Monitoring
- **Logs**: Structured logging for performance analysis
- **Metrics**: Success/failure rates by operation type
- **Alerts**: Automatic alerts for performance degradation
- **Reports**: Weekly performance summaries

---

## 🔐 Security Considerations

### API Keys
- **Storage**: API keys in gitignored files, never in code
- **Rotation**: Regular key rotation schedule
- **Access**: Principle of least privilege for API access

### Data Handling
- **Validation**: Input validation for all external data
- **Sanitization**: File path and metadata sanitization
- **Encryption**: Secure storage of sensitive configuration

### Network Security
- **HTTPS**: All API communications over HTTPS
- **Verification**: SSL certificate verification
- **Timeouts**: Reasonable timeouts for all network operations

---

## 📚 Documentation Standards

### README Structure
- **Quick Start**: Installation and basic usage
- **Configuration**: Detailed configuration options
- **Examples**: Real-world usage examples
- **Troubleshooting**: Common issues and solutions
- **Contributing**: Development setup and guidelines

### Code Documentation
- **API Docs**: Sphinx-generated API documentation
- **Inline Comments**: Complex logic explanation
- **Type Hints**: Complete type annotation coverage
- **Examples**: Usage examples in docstrings

---

## 🎯 Future Vision

### Short Term (3-6 months)
- **Enhanced Testing**: Comprehensive test suite with CI/CD
- **Performance Optimization**: Bulk operation optimization
- **Additional Trackers**: Expand tracker support
- **User Experience**: Better error messages and progress feedback

### Medium Term (6-12 months)
- **Web Interface**: Optional dashboard for management
- **Database Integration**: Persistent metadata storage
- **Advanced Matching**: ML-based title and content matching
- **API Improvements**: GraphQL, real-time updates

### Long Term (1+ years)
- **Microservices Architecture**: Service-based design
- **Cloud Integration**: Cloud storage and processing
- **Mobile Support**: Mobile app for remote management
- **Enterprise Features**: Multi-user, role-based access

---

## 📞 Contact & Support

### Development Issues
- **GitHub Issues**: Use issue templates for bug reports
- **Discussions**: Feature requests and general questions
- **Code Reviews**: PR reviews for code quality

### User Support
- **Documentation**: Comprehensive documentation and examples
- **Troubleshooting**: Detailed problem-solving guides
- **Community**: Active support and knowledge sharing

---

*Last Updated: 2026-01-04*  
*Version: 1.0.0*  
*Maintainers: Benjamin SCHWALD <b.schwald@majyx.net>*

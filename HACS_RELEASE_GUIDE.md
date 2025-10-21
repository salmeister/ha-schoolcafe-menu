# HACS Release Guide

## Version Format Requirements

HACS requires **semantic versioning** in the format: `MAJOR.MINOR.PATCH`

### ✅ Good Version Examples:
- `1.0.0` - Initial release
- `1.1.0` - New features added
- `1.1.1` - Bug fixes
- `2.0.0` - Breaking changes

### ❌ Bad Version Examples (HACS will reject):
- `2025.10.21` - Date-based versioning
- `2025.10.21.2` - Date with patch number
- `v25.10.21` - Non-standard format

## How to Create a Proper Release

### Method 1: GitHub Web Interface (Recommended)
1. Go to your repository on GitHub
2. Click "Releases" → "Create a new release"
3. **Tag version**: Enter `v1.2.0` (with 'v' prefix)
4. **Release title**: "Version 1.2.0"
5. **Description**: List changes and improvements
6. Click "Publish release"

### Method 2: Command Line
```bash
# Create and push a semantic version tag
git tag v1.2.0
git push origin v1.2.0

# Then create a release on GitHub using the tag
```

## Current Version Status

### Files Updated:
- `manifest.json` → version "1.1.0"
- `hacs.json` → HACS configuration file added
- GitHub workflows added for validation

### Git Tags:
- ✅ `v1.1.0` - Current semantic version (HACS compatible)
- ❌ `2025.10.21.2` - Old date-based tags (should be ignored by HACS now)

## Fixing the Current Issue

The error you're seeing:
```
The version 2025.10.21.2 for this integration can not be used with HACS.
```

Is caused by the date-based git tags in your repository. 

### Solution Applied:
1. ✅ Updated `manifest.json` to use semantic versioning
2. ✅ Created `hacs.json` configuration file
3. ✅ Added git tag `v1.1.0` with proper format
4. ✅ Added GitHub workflows for validation

### Next Steps:
1. **In HACS**: Try installing again - it should now use version 1.1.0
2. **For future releases**: Always use semantic versioning (1.2.0, 1.3.0, etc.)
3. **Optional cleanup**: You can delete the old date-based tags if desired

## Semantic Versioning Guidelines

When to increment each number:

### MAJOR (1.x.x → 2.x.x)
- Breaking changes
- Incompatible API changes
- Major rework of functionality

### MINOR (x.1.x → x.2.x)
- New features added
- New sensor attributes
- Enhanced functionality
- Backward compatible changes

### PATCH (x.x.1 → x.x.2)  
- Bug fixes
- Small improvements
- Documentation updates
- No new features

## Example Release History
```
v1.0.0 - Initial release
v1.1.0 - Added is_weekday attribute and improved sensor naming
v1.1.1 - Fixed manifest.json for HACS compatibility
v1.2.0 - Added new menu filtering features
v2.0.0 - Breaking: Complete sensor naming overhaul
```

## Testing HACS Compatibility

The repository now includes a GitHub workflow (`.github/workflows/hacs.yml`) that automatically validates HACS compatibility on every push.

This will catch version format issues before they become a problem!
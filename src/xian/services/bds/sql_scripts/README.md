# SQL Scripts

This directory contains standalone SQL scripts for BDS database operations.

## Available Scripts

### `fix_value_numeric.py`
Fixes the `value_numeric` columns in `state` and `state_changes` tables to properly handle scientific notation.

**Usage:**
```bash
cd xian-core/src/xian/services/bds/
python sql_scripts/fix_value_numeric.py
```

**What it does:**
- Drops existing `value_numeric` columns
- Recreates them with regex that supports scientific notation (e.g., `1e10`, `2.5E-3`)
- Recreates the index on `state.value_numeric`

**⚠️ Important:** 
- Backup your database before running
- This will recalculate all `value_numeric` values which may take time on large databases

## Adding New Scripts

When adding new SQL scripts to this folder:
1. Create a descriptive filename
2. Add proper logging and error handling  
3. Include a docstring explaining what the script does
4. Update this README with usage instructions 
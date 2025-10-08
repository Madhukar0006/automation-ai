# 🕐 VRL Timestamp Functions - Quick Reference

## ✅ **CORRECT: For Timestamp Strings**

```vrl
# Use parse_timestamp!() for timestamp STRINGS
if exists(.timestamp) {
  .@timestamp = parse_timestamp!(.timestamp, "%Y-%m-%dT%H:%M:%S%.fZ") ?? now()
}
```

**Common Formats:**
```vrl
# ISO8601 with milliseconds
.@timestamp = parse_timestamp!(.ts, "%Y-%m-%dT%H:%M:%S%.fZ") ?? now()

# ISO8601 without milliseconds  
.@timestamp = parse_timestamp!(.ts, "%Y-%m-%dT%H:%M:%SZ") ?? now()

# Standard datetime
.@timestamp = parse_timestamp!(.ts, "%Y-%m-%d %H:%M:%S") ?? now()

# Syslog format
.@timestamp = parse_timestamp!(.ts, "%b %d %H:%M:%S") ?? now()

# Apache log format
.@timestamp = parse_timestamp!(.ts, "%d/%b/%Y:%H:%M:%S %z") ?? now()
```

---

## ✅ **CORRECT: For Unix Timestamps (Integers)**

```vrl
# Use to_timestamp!() for Unix epoch INTEGERS
if exists(.unix_timestamp) {
  .@timestamp = to_timestamp!(.unix_timestamp)
}

# Milliseconds
if exists(.timestamp_ms) {
  .@timestamp = to_timestamp!(.timestamp_ms / 1000)
}
```

---

## ❌ **WRONG: Don't Do This**

```vrl
# ❌ WRONG - to_timestamp!() doesn't work on strings
if exists(.timestamp) { .@timestamp = to_timestamp!(.timestamp) }
#                                     ^^^^^^^^^^^^^^^^^^^^^^^^
#                                     undefined function error!

# ❌ WRONG - is_timestamp() doesn't parse
if exists(.timestamp) { .@timestamp = is_timestamp(.timestamp) }
```

---

## 📋 **Format String Reference**

| Symbol | Meaning | Example |
|--------|---------|---------|
| `%Y` | 4-digit year | 2024 |
| `%m` | 2-digit month | 01-12 |
| `%d` | 2-digit day | 01-31 |
| `%H` | 2-digit hour (24h) | 00-23 |
| `%M` | 2-digit minute | 00-59 |
| `%S` | 2-digit second | 00-59 |
| `%.f` | Fractional seconds | .123 |
| `%z` | Timezone offset | +0000 |
| `%b` | Short month name | Jan |
| `%F` | Date (shorthand) | %Y-%m-%d |
| `%T` | Time (shorthand) | %H:%M:%S |

---

## 🛡️ **Safe Pattern (Recommended)**

```vrl
# Always include ?? now() fallback for safety
.@timestamp = parse_timestamp!(.timestamp, "%Y-%m-%dT%H:%M:%S%.fZ") ?? now()

# Alternative with error checking
parsed_ts, err = parse_timestamp(.timestamp, "%Y-%m-%dT%H:%M:%S%.fZ")
if err == null {
  .@timestamp = parsed_ts
} else {
  .@timestamp = now()
  .parse_error = err
}
```

---

## 🎯 **Quick Decision Tree**

```
Is your timestamp a STRING (e.g., "2024-01-15T10:30:45Z")?
  ↓ YES
  → Use parse_timestamp!(.field, "format") ?? now()

Is your timestamp an INTEGER (e.g., 1705318245)?
  ↓ YES  
  → Use to_timestamp!(.field)

Not sure what type it is?
  ↓
  → Try both with type checking:
    if is_string(.timestamp) {
      .@timestamp = parse_timestamp!(.timestamp, "%Y-%m-%dT%H:%M:%S%.fZ") ?? now()
    } else if is_integer(.timestamp) {
      .@timestamp = to_timestamp!(.timestamp)
    } else {
      .@timestamp = now()
    }
```

---

## 📚 **Additional Timestamp Functions**

| Function | Purpose | Example |
|----------|---------|---------|
| `now()` | Current timestamp | `.@timestamp = now()` |
| `format_timestamp!()` | Format timestamp to string | `.time_str = format_timestamp!(now(), "%Y-%m-%d")` |
| `is_timestamp()` | Check if value is timestamp | `if is_timestamp(.field) { ... }` |

---

## 💡 **Remember**

- ✅ **Strings** → `parse_timestamp!()`
- ✅ **Integers** → `to_timestamp!()`  
- ✅ **Always** → use `?? now()` fallback
- ❌ **Never** → `to_timestamp!()` on strings

---

**See `FIXED_GPT4_TIMESTAMP_ISSUE.md` for full details**

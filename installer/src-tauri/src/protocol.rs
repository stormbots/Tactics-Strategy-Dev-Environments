use serde::Serialize;

#[derive(Clone, Debug, Serialize, PartialEq)]
pub struct Event {
    pub kind: String,
    pub key: String,
    pub message: String,
}

pub fn parse(line: &str) -> Option<Event> {
    let mut parts = line.trim_end_matches(['\r', '\n']).splitn(4, '|');
    if parts.next()? != "SKYVIEW_EVENT" {
        return None;
    }
    let kind = parts.next()?;
    let key = parts.next()?;
    let message = parts.next()?;
    match kind {
        "progress" => {
            let n = key.parse::<u8>().ok()?;
            if n > 100 {
                return None;
            }
        }
        "validation" if !["PASS", "WARNING", "FAIL", "INFO"].contains(&key) => return None,
        "summary" if key.parse::<u32>().is_err() => return None,
        "phase" | "status" | "warning" | "error" | "validation" | "summary" | "update" | "tool" => {
        }
        _ => return None,
    }
    Some(Event {
        kind: kind.into(),
        key: key.into(),
        message: message.into(),
    })
}

pub fn validated_success(code: i32, lines: &[String]) -> bool {
    code == 0
        && lines
            .iter()
            .filter_map(|s| parse(s))
            .any(|e| e.kind == "summary" && e.key == "0")
        && !lines
            .iter()
            .filter_map(|s| parse(s))
            .any(|e| e.kind == "validation" && e.key == "FAIL")
}

pub fn redact(line: &str) -> String {
    use regex::Regex;
    use std::sync::OnceLock;
    static SECRETS: OnceLock<Regex> = OnceLock::new();
    static URLS: OnceLock<Regex> = OnceLock::new();
    let secrets = SECRETS.get_or_init(|| Regex::new(r"(?i)(gh[pousr]_[a-z0-9_]+|github_pat_[a-z0-9_]+|(?:token|password|authorization|api[_-]?key)\s*[:=]\s*\S+)").unwrap());
    let urls = URLS.get_or_init(|| Regex::new(r"https?://[^\s/@]+(?::[^\s/@]*)?@").unwrap());
    urls.replace_all(
        &secrets.replace_all(line, "[REDACTED]"),
        "https://[REDACTED]@",
    )
    .into_owned()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parses_protocol_without_scraping() {
        assert_eq!(
            parse("SKYVIEW_EVENT|progress|45|Installing | editor\r\n")
                .unwrap()
                .message,
            "Installing | editor"
        );
        assert!(parse("Installing Node: 45% complete").is_none());
        for bad in [
            "SKYVIEW_EVENT|progress|-1|bad",
            "SKYVIEW_EVENT|progress|101|bad",
            "SKYVIEW_EVENT|validation|OK|bad",
            "SKYVIEW_EVENT|summary|oops|bad",
            "SKYVIEW_EVENT|x|y|z",
        ] {
            assert!(parse(bad).is_none());
        }
    }
    #[test]
    fn requires_exit_and_validation() {
        let good = vec!["SKYVIEW_EVENT|summary|0|Done".into()];
        assert!(validated_success(0, &good));
        assert!(!validated_success(1, &good));
        assert!(!validated_success(0, &[]));
        let bad = vec!["SKYVIEW_EVENT|validation|FAIL|Node".into(), good[0].clone()];
        assert!(!validated_success(0, &bad));
    }
    #[test]
    fn removes_credentials() {
        let clean = redact("git https://student:secret@github.com/repo ghp_abc123 token=secret");
        assert!(!clean.contains("secret"));
        assert!(!clean.contains("ghp_abc123"));
    }
}

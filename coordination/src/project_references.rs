//! Data-only format for future ordinary-user project-location consumers.
//! Decoding neither inspects a folder nor grants Save, Open or execution authority.
use serde::Deserialize;
use std::collections::HashSet;

pub const MAX_BYTES: usize = 16_384;
pub const MAX_PROJECTS: usize = 64;
const MAX_PATH_BYTES: usize = 4096;
const MAX_REVISION: u64 = 9_007_199_254_740_991;

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Platform {
    Windows,
    Linux,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct WireProjectBinding {
    project_id: String,
    path: String,
}

#[derive(Debug)]
pub struct ProjectBinding(WireProjectBinding);

impl ProjectBinding {
    pub fn project_id(&self) -> &str {
        &self.0.project_id
    }

    pub fn path(&self) -> &str {
        &self.0.path
    }
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireReferences {
    schema: u32,
    platform: Platform,
    revision: u64,
    workspace: String,
    projects: Vec<WireProjectBinding>,
}

#[derive(Debug)]
pub struct References {
    revision: u64,
    workspace: String,
    projects: Vec<ProjectBinding>,
}

impl References {
    pub fn revision(&self) -> u64 {
        self.revision
    }

    pub fn workspace(&self) -> &str {
        &self.workspace
    }

    pub fn projects(&self) -> &[ProjectBinding] {
        &self.projects
    }
}

#[derive(Debug, PartialEq, Eq)]
pub enum DecodeError {
    Size,
    Malformed,
    UnsupportedSchema,
    WrongPlatform,
    InvalidRevision,
    UnsupportedPath,
    InvalidBindings,
}

fn project_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value != ".."
        && value.bytes().enumerate().all(|(i, c)| {
            c.is_ascii_alphanumeric() || c == b'_' || c == b'-' || (i > 0 && c == b'.')
        })
}

fn path(value: &str, platform: Platform) -> bool {
    if value.is_empty()
        || value.len() > MAX_PATH_BYTES
        || value.chars().any(|c| {
            c.is_control()
                || c == '|'
                || matches!(c, '\u{202a}'..='\u{202e}' | '\u{2066}'..='\u{2069}')
        })
    {
        return false;
    }
    let parts = match platform {
        Platform::Linux => {
            if value == "/" {
                return true;
            }
            let Some(rest) = value.strip_prefix('/') else {
                return false;
            };
            rest.split('/').collect::<Vec<_>>()
        }
        Platform::Windows => {
            let bytes = value.as_bytes();
            if bytes.len() < 3
                || !bytes[0].is_ascii_alphabetic()
                || &bytes[1..3] != b":\\"
                || value.contains('/')
            {
                return false;
            }
            if bytes.len() == 3 {
                return true;
            }
            let parts = value[3..].split('\\').collect::<Vec<_>>();
            if parts.iter().any(|part| {
                let stem = part.split('.').next().unwrap_or("").to_ascii_uppercase();
                part.ends_with(['.', ' '])
                    || part.contains([':', '*', '?', '<', '>', '"'])
                    || matches!(stem.as_str(), "CON" | "PRN" | "AUX" | "NUL")
                    || (stem.len() == 4
                        && (stem.starts_with("COM") || stem.starts_with("LPT"))
                        && matches!(stem.as_bytes()[3], b'1'..=b'9'))
            }) {
                return false;
            }
            parts
        }
    };
    parts.iter().all(|part| !matches!(*part, "" | "." | ".."))
}

/// Decode bounded bytes without filesystem access, normalization or fallback.
/// The caller must distinguish an absent record from any read/decoding failure.
/// A decoded path may be disconnected, unreadable, replaced or the wrong project.
/// Live ordinary-user inspection and reviewed operation context remain mandatory.
pub fn decode(bytes: &[u8], platform: Platform) -> Result<References, DecodeError> {
    if bytes.is_empty() || bytes.len() > MAX_BYTES {
        return Err(DecodeError::Size);
    }
    // Deserialize directly into structs: a Value/map intermediate loses duplicate
    // keys, which must remain errors even when their values are identical.
    let record: WireReferences =
        serde_json::from_slice(bytes).map_err(|_| DecodeError::Malformed)?;
    if record.schema != 1 {
        return Err(DecodeError::UnsupportedSchema);
    }
    if record.platform != platform {
        return Err(DecodeError::WrongPlatform);
    }
    if record.revision == 0 || record.revision > MAX_REVISION {
        return Err(DecodeError::InvalidRevision);
    }
    if !path(&record.workspace, platform) {
        return Err(DecodeError::UnsupportedPath);
    }
    if record.projects.len() > MAX_PROJECTS {
        return Err(DecodeError::InvalidBindings);
    }
    let mut ids = HashSet::new();
    for binding in &record.projects {
        if !project_id(&binding.project_id) || !ids.insert(&binding.project_id) {
            return Err(DecodeError::InvalidBindings);
        }
        if !path(&binding.path, platform) {
            return Err(DecodeError::UnsupportedPath);
        }
    }
    Ok(References {
        revision: record.revision,
        workspace: record.workspace,
        projects: record.projects.into_iter().map(ProjectBinding).collect(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::{json, Value};

    fn record() -> Value {
        json!({"schema":1,"platform":"linux","revision":1,"workspace":"/home/student/Development",
            "projects":[{"projectId":"robot-code","path":"/media/student/School/robot"}]})
    }

    fn error(value: &Value, expected: DecodeError) {
        assert_eq!(
            decode(&serde_json::to_vec(value).unwrap(), Platform::Linux).unwrap_err(),
            expected
        );
    }

    #[test]
    fn retains_explicit_outside_workspace_binding_and_revision() {
        let value = record();
        let decoded = decode(&serde_json::to_vec(&value).unwrap(), Platform::Linux).unwrap();
        assert_eq!(decoded.revision(), 1);
        assert_eq!(decoded.workspace(), "/home/student/Development");
        assert_eq!(decoded.projects()[0].project_id(), "robot-code");
        assert_eq!(decoded.projects()[0].path(), "/media/student/School/robot");
    }

    #[test]
    fn decoding_does_not_require_folder_to_exist_or_run_substitutions() {
        let mut value = record();
        value["workspace"] = json!("/unmounted/Étudiant 你好/$(do-not-run)`literal`");
        let decoded = decode(&serde_json::to_vec(&value).unwrap(), Platform::Linux).unwrap();
        assert_eq!(decoded.workspace(), value["workspace"].as_str().unwrap());
        value["projects"] = json!([]);
        assert!(decode(&serde_json::to_vec(&value).unwrap(), Platform::Linux).is_ok());
    }

    #[test]
    fn rejects_unknown_duplicate_and_authority_fields_at_each_level() {
        for (a, b) in [
            ("\"schema\":1", "\"schema\":1,\"schema\":1"),
            ("\"path\":", "\"path\":\"/other\",\"path\":"),
        ] {
            let text = serde_json::to_string(&record()).unwrap().replace(a, b);
            assert_eq!(
                decode(text.as_bytes(), Platform::Linux).unwrap_err(),
                DecodeError::Malformed
            );
        }
        for field in ["command", "readiness", "maintenanceGrant", "acknowledged"] {
            let mut value = record();
            value[field] = json!(true);
            error(&value, DecodeError::Malformed);
            let mut value = record();
            value["projects"][0][field] = json!(true);
            error(&value, DecodeError::Malformed);
        }
    }

    #[test]
    fn refuses_partial_null_and_mistyped_records() {
        for field in ["schema", "platform", "revision", "workspace", "projects"] {
            let mut value = record();
            value.as_object_mut().unwrap().remove(field);
            error(&value, DecodeError::Malformed);
            value[field] = Value::Null;
            error(&value, DecodeError::Malformed);
        }
        for value in [json!({}), json!([]), json!(false), json!("saved")] {
            error(&value, DecodeError::Malformed);
        }
        let mut value = record();
        value["projects"][0].as_object_mut().unwrap().remove("path");
        error(&value, DecodeError::Malformed);
    }

    #[test]
    fn rejects_wrong_schema_platform_and_noninteger_or_unsafe_revisions() {
        let mut value = record();
        value["schema"] = json!(2);
        error(&value, DecodeError::UnsupportedSchema);
        value = record();
        value["platform"] = json!("windows");
        error(&value, DecodeError::WrongPlatform);
        value["platform"] = json!("unknown");
        error(&value, DecodeError::Malformed);
        for revision in [json!(0), json!(MAX_REVISION + 1)] {
            value = record();
            value["revision"] = revision;
            error(&value, DecodeError::InvalidRevision);
        }
        for revision in [json!(-1), json!(1.5), json!(true), json!("1")] {
            value = record();
            value["revision"] = revision;
            error(&value, DecodeError::Malformed);
        }
    }

    #[test]
    fn rejects_malformed_utf8_trailing_json_bom_and_size_overflow() {
        for bytes in [&b"\xff"[..], b"{} {}", b"\xef\xbb\xbf{}", b"{"] {
            assert_eq!(
                decode(bytes, Platform::Linux).unwrap_err(),
                DecodeError::Malformed
            );
        }
        assert_eq!(decode(&[], Platform::Linux).unwrap_err(), DecodeError::Size);
        let bytes = serde_json::to_vec(&record()).unwrap();
        let mut padded = bytes;
        padded.resize(MAX_BYTES, b' ');
        assert!(decode(&padded, Platform::Linux).is_ok());
        padded.push(b' ');
        assert_eq!(
            decode(&padded, Platform::Linux).unwrap_err(),
            DecodeError::Size
        );
    }

    #[test]
    fn bounds_binding_count_and_project_identifiers_without_merging_clones() {
        let mut value = record();
        value["projects"] = json!((0..MAX_PROJECTS)
            .map(|i| json!({"projectId":format!("course-{i}"),"path":format!("/school/clone-{i}")}))
            .collect::<Vec<_>>());
        assert!(decode(&serde_json::to_vec(&value).unwrap(), Platform::Linux).is_ok());
        value["projects"]
            .as_array_mut()
            .unwrap()
            .push(json!({"projectId":"extra","path":"/extra"}));
        error(&value, DecodeError::InvalidBindings);
        for id in ["", "..", ".git", "two words", "a/b", "a\\b", "é"] {
            value = record();
            value["projects"][0]["projectId"] = json!(id);
            error(&value, DecodeError::InvalidBindings);
        }
        value = record();
        value["projects"][0]["projectId"] = json!("a".repeat(129));
        error(&value, DecodeError::InvalidBindings);
        value = record();
        let duplicate = value["projects"][0].clone();
        value["projects"].as_array_mut().unwrap().push(duplicate);
        error(&value, DecodeError::InvalidBindings);
    }

    #[test]
    fn rejects_relative_ambiguous_control_and_oversized_linux_paths() {
        for path in [
            "",
            "relative",
            "~/Development",
            "//server/share",
            "/a/../b",
            "/a/./b",
            "/a/",
            "/a//b",
            "/a|b",
            "/a\nb",
            "/a\u{202e}b",
            "/a\u{2067}b",
        ] {
            let mut value = record();
            value["workspace"] = json!(path);
            error(&value, DecodeError::UnsupportedPath);
            value = record();
            value["projects"][0]["path"] = json!(path);
            error(&value, DecodeError::UnsupportedPath);
        }
        let mut value = record();
        value["workspace"] = json!(format!("/{}", "a".repeat(MAX_PATH_BYTES)));
        error(&value, DecodeError::UnsupportedPath);
        value["workspace"] = json!("/");
        assert!(decode(&serde_json::to_vec(&value).unwrap(), Platform::Linux).is_ok());
    }

    #[test]
    fn windows_local_paths_preserve_spelling_and_reject_device_and_alias_forms() {
        let mut value = record();
        value["platform"] = json!("windows");
        value["projects"] = json!([]);
        for path in [
            r"C:\",
            r"d:\School Projects\Étudiant 你好\robot",
            r"C:\Development",
        ] {
            value["workspace"] = json!(path);
            let decoded = decode(&serde_json::to_vec(&value).unwrap(), Platform::Windows).unwrap();
            assert_eq!(decoded.workspace(), path);
        }
        for path in [
            r"C:relative",
            r"C:/Development",
            r"\\server\share",
            r"\\?\C:\Development",
            r"\root",
            r"C:\a\..\b",
            r"C:\a\",
            r"C:\a\\b",
            r"C:\a:stream",
            r"C:\NUL.txt",
            r"C:\COM1",
            r"C:\a.",
            "C:\\a ",
            r"C:\*",
            "/home/student",
        ] {
            value["workspace"] = json!(path);
            assert_eq!(
                decode(&serde_json::to_vec(&value).unwrap(), Platform::Windows).unwrap_err(),
                DecodeError::UnsupportedPath,
                "{path}"
            );
        }
    }
}

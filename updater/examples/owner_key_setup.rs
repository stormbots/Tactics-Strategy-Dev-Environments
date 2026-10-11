// Owner-only setup utility. Never outputs private material.
use std::{
    fs::{self, OpenOptions},
    io::{Cursor, Write},
    path::Path,
};
fn main() {
    if run().is_err() {
        eprintln!(
            "Key setup failed; inspect protected backup files without displaying them in logs."
        );
        std::process::exit(1);
    }
}
fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 1 {
        return Err("Provide protected backup directory".into());
    }
    let dir = Path::new(&args[0]);
    let password = fs::read_to_string(dir.join("release.passphrase"))?;
    let mut public = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(dir.join("release.pub"))?;
    let mut private = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(dir.join("release.key"))?;
    let keys = minisign::KeyPair::generate_and_write_encrypted_keypair(
        &mut public,
        &mut private,
        Some("SDE dedicated release signing key"),
        Some(password.clone()),
    )?;
    public.sync_all()?;
    private.sync_all()?;
    // Restore the serialized backup and prove it can sign and verify.
    let restored = minisign::SecretKey::from_box(
        fs::read_to_string(dir.join("release.key"))?.into(),
        Some(password),
    )?;
    let message = b"SDE encrypted signing backup recovery test";
    let signature = minisign::sign(Some(&keys.pk), &restored, Cursor::new(message), None, None)?;
    minisign::verify(
        &keys.pk,
        &signature,
        Cursor::new(message),
        true,
        false,
        false,
    )?;
    let mut receipt = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(dir.join("BACKUP-README.txt"))?;
    receipt.write_all(b"SDE dedicated Minisign signing recovery backup. release.key is encrypted; release.passphrase is its recovery password. Directory and files are owner-only. Copy the encrypted key and public key to offline encrypted storage; keep the passphrase in your password manager separately. Do not upload, commit, or display release.key/release.passphrase. The restored encrypted backup was tested by signing and verifying a disposable message. GitHub environment: sde-release-signing. Secrets: SDE_UPDATE_SIGNING_KEY and SDE_UPDATE_SIGNING_PASSWORD.\n")?;
    receipt.sync_all()?;
    println!("Encrypted backup generated and recovery-tested; no private material displayed.");
    Ok(())
}

#!/usr/bin/env bash
# Build an actual Mint userland from its signed official ISO, never relabel Ubuntu.
set -Eeuo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && -n "${RUNNER_TEMP:-}" ]] || exit 1
root="$RUNNER_TEMP/sde-mint-native-image"
mkdir -p "$root/gpg"
chmod 0700 "$root/gpg"
iso=linuxmint-22.3-xfce-64bit.iso
base=https://pub.linuxmint.io/stable/22.3
curl --fail --location --retry 3 "$base/sha256sum.txt" -o "$root/sha256sum.txt"
curl --fail --location --retry 3 "$base/sha256sum.txt.gpg" -o "$root/sha256sum.txt.gpg"
gpg --batch --homedir "$root/gpg" --import tests/fixtures/linuxmint-iso-signing.asc
gpg --batch --homedir "$root/gpg" --with-colons --fingerprint | grep -q '^fpr:::::::::27DEB15644C6B3CF3BD7D291300F846BA25BAE09:'
gpg --batch --homedir "$root/gpg" --verify "$root/sha256sum.txt.gpg" "$root/sha256sum.txt"
expected=45a835b5dddaf40e84d776549e0b19b3fbd49673b6cc6434ebddbfcd217df776
grep -Fxq "$expected *$iso" "$root/sha256sum.txt"
curl --fail --location --retry 3 "$base/$iso" -o "$root/$iso"
printf '%s  %s\n' "$expected" "$root/$iso" | sha256sum --check
sudo apt-get install -y p7zip-full squashfs-tools
7z e "$root/$iso" -o"$root" casper/filesystem.squashfs
sudo unsquashfs -no-progress -d "$root/filesystem" "$root/filesystem.squashfs"
sudo tar -C "$root/filesystem" -c . | docker import - sde-mint22.3-native
# These are fixed disposable extraction paths in the Actions temporary directory.
sudo rm -rf -- "$root/filesystem"
rm -- "$root/$iso" "$root/filesystem.squashfs"
docker run --rm --entrypoint /bin/cat sde-mint22.3-native /etc/os-release

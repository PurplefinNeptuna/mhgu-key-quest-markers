use std::env;
// Supply native linker flags and the two requested build-time emblem identities.
fn main() {
    let dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    println!("cargo:rustc-link-arg=-T{dir}/link/switch32.ld");
    println!("cargo:rustc-link-arg=-Wl,--build-id=sha1");
    println!("cargo:rerun-if-changed=link/switch32.ld");
    println!("cargo:rerun-if-env-changed=KQM_SMALL_MARK");
    println!("cargo:rerun-if-env-changed=KQM_VERSION");
    println!("cargo:rustc-check-cfg=cfg(kqm_small_mark)");
    if env::var("KQM_SMALL_MARK").as_deref() == Ok("1") {
        println!("cargo:rustc-cfg=kqm_small_mark");
    }
    println!(
        "cargo:rustc-env=KQM_VERSION={}",
        env::var("KQM_VERSION").unwrap()
    );
}

"""Check the integrity, sample roster, and publication eligibility of a bundle."""

from .io import fingerprint, read_json, sha256
from .metrics import adapter_result
from .provenance import lock_digests, source
from .registry import DIGEST, ID, index, load, select, validate_case
from .runner import SCHEMA, compatible_sample, paths_for, planned_samples


def validate(bundle, *, publication=False):
    manifest = read_json(bundle / "manifest.json")
    if manifest.get("state") != "complete":
        raise ValueError(f"Incomplete run: {bundle}")
    if manifest.get("schema_version") != SCHEMA or not ID.fullmatch(manifest["run_id"]):
        raise ValueError("Invalid bundle ID or schema version")
    if type(manifest["repeats"]) is not int or manifest["repeats"] < 1:
        raise ValueError("Invalid repeat count")
    cases = index(manifest["cases"], "case")
    if not cases or cases.keys() != manifest["inputs"].keys():
        raise ValueError("Manifest cases and inputs disagree")
    identity = {key: value for key, value in manifest.items()
                if key not in {"started_at", "finished_at", "state", "run_fingerprint"}}
    signature = fingerprint(identity)
    if signature != manifest["run_fingerprint"]:
        raise ValueError("Invalid run fingerprint")
    expected_files = {"manifest.json"}
    rows = []
    for key, case, repeat in planned_samples(manifest):
        record = manifest["inputs"][case["id"]]
        dataset = record.get("dataset")
        datasets = {dataset["id"]: dataset} if dataset else {}
        validate_case(case, datasets, case["profiles"])
        if manifest["profile"] not in case["profiles"]:
            raise ValueError(f"Case {case['id']} does not belong to the run profile")
        if dataset:
            if record.get("verified") is True:
                if record.get("sha256") != dataset.get("sha256") or not DIGEST.fullmatch(record["sha256"]):
                    raise ValueError(f"Invalid dataset checksum for {case['id']}")
            elif not record.get("reason"):
                raise ValueError(f"Missing dataset availability evidence for {case['id']}")
        elif record.get("fixture") != case.get("fixture"):
            raise ValueError(f"Fixture mismatch for {case['id']}")
        path, log = paths_for(bundle, key)
        if not compatible_sample(path, log, key, case, repeat, signature):
            raise ValueError(f"Missing sample {key}")
        result = adapter_result(case, read_json(path)["result"])
        if record.get("reason") and result["status"] != "unavailable":
            raise ValueError(f"Sample {key} used an unverified input")
        expected_files.update(file.relative_to(bundle).as_posix() for file in (path, log))
        rows.append((case, key, result))
    checksums_path = bundle / "checksums.json"
    checksums = read_json(checksums_path)
    paths = list(bundle.rglob("*"))
    files = {path.relative_to(bundle).as_posix() for path in paths if path.is_file()}
    if (any(path.is_symlink() for path in paths) or checksums.keys() != expected_files
            or files != expected_files | {"checksums.json"}):
        raise ValueError("Bundle inventory does not match the expected roster")
    for name, digest in checksums.items():
        if sha256(bundle / name) != digest:
            raise ValueError(f"Checksum mismatch: {name}")
    if publication:
        check_publication(manifest, rows)
    return manifest, rows


def check_publication(manifest, rows):
    if (manifest["profile"] not in {"standard", "extended"}
            or not manifest["publishable_profile"] or not manifest["full_profile"]):
        raise ValueError("Publication requires a full standard or extended profile")
    if (manifest["series"] == "local" or not manifest["source"]["commit"]
            or manifest["source"]["dirty"] is not False):
        raise ValueError("Publication requires a named series and clean source revision")
    image = manifest["environment"]["image_digest"] or ""
    if not image.startswith("sha256:") or not DIGEST.fullmatch(image.removeprefix("sha256:")):
        raise ValueError("Publication requires a pinned image digest")
    if not manifest["environment"]["lock_sha256"]:
        raise ValueError("Publication requires checksums for dependency locks")
    accepted = {"ok", "expected_rejection", "unavailable", "unsupported"}
    unexpected = [sample for case, sample, value in rows
                  if value["status"] not in accepted.intersection(case["expected"])]
    if unexpected:
        raise ValueError(f"{len(unexpected)} unexpected outcomes, starting with {unexpected[0]}")
    if not any(value["status"] == "ok" for _, _, value in rows):
        raise ValueError("Publication requires at least one successful sample")


def check_roster(repo, manifest):
    observed = source(repo)
    if observed["commit"] != manifest["source"]["commit"] or observed["dirty"] is not False:
        raise ValueError("Roster verification requires a clean checkout of the run revision")
    profiles, cases, datasets = load(repo)
    profile = manifest["profile"]
    chosen = () if manifest["full_profile"] else [case["id"] for case in manifest["cases"]]
    roster = select(cases, profiles, profile, chosen)
    settings = profiles[profile]
    if (roster != manifest["cases"] or settings["repeats"] != manifest["repeats"]
            or settings["publishable"] != manifest["publishable_profile"]):
        raise ValueError("Run roster or repeat count differs from the source registry")
    for case in roster:
        if case.get("dataset"):
            if datasets[case["dataset"]] != manifest["inputs"][case["id"]].get("dataset"):
                raise ValueError(f"Dataset manifest mismatch for {case['id']}")
    if lock_digests(repo) != manifest["environment"]["lock_sha256"]:
        raise ValueError("Dependency locks differ from the source registry")

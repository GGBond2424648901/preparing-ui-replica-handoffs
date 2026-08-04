import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

from PIL import Image, ImageChops


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = (
    REPOSITORY_ROOT / "skill" / "preparing-ui-replica-handoffs" / "scripts"
)
PREPARE_PATH = SCRIPTS_ROOT / "prepare_handoff.py"
VALIDATE_PATH = SCRIPTS_ROOT / "validate_handoff.py"


def _load_module(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


PREPARE = _load_module(PREPARE_PATH, "prepare_handoff_for_validation_tests")


def _write_image(path, size=(18, 12), color="navy", image_format="PNG"):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format=image_format)


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path, document):
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record_set_hash(records):
    digest = hashlib.sha256()
    for relative_path, file_hash in records:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


SECTION_CONTRACT_FIELDS = {
    "identity-and-evidence": (
        "pageId",
        "stateId",
        "variantId",
        "sourceAssetIds",
        "route",
        "evidenceLevel",
        "status",
    ),
    "canvas-shell-regions": ("canvas", "shell", "regions"),
    "layout-copy-icons-data": ("layoutRelationships", "copy", "icons", "data"),
    "components-interactions-responsive": (
        "components",
        "interactions",
        "responsiveVariants",
    ),
    "qa-and-gaps": ("acceptanceCriteria", "gapIds"),
}


def _contract_hash(page, section_id):
    subset = {field: page.get(field) for field in SECTION_CONTRACT_FIELDS[section_id]}
    canonical = json.dumps(
        subset, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _write_complete_page_documents(handoff, page, registry):
    identity = f"{page['pageId']}-{page['stateId']}-{page['variantId']}"
    source_link = next(
        asset["deliveryRelativePath"]
        for asset in _read_json(handoff / "contracts" / "asset-manifest.json")["assets"]
        if asset["assetId"] == page["sourceAssetIds"][0]
    )
    component_names = {
        component["componentId"]: component["name"]
        for component in registry["components"]
    }
    for locale, locale_code in (("zh", "zh-CN"), ("en", "en-US")):
        path = next((handoff / "docs" / locale / "pages").glob(f"{identity}-*.md"))
        if locale == "zh":
            prose = {
                "identity-and-evidence": "本节确认页面身份、设计来源与批准状态，所有实施工作都必须追溯到列出的原始设计资产和固定路由证据。",
                "canvas-shell-regions": "本节定义原生画布、应用外壳和完整区域边界；开发时保持坐标、尺寸、滚动方式与区域层级关系不变。",
                "layout-copy-icons-data": "本节记录布局关系、可见文案、图标语义和数据形状；每一项均按设计证据实现并用于逐项视觉验收。",
                "components-interactions-responsive": "本节约束组件实例、交互结果和响应式变体；实现必须使用登记组件并准确复现声明的用户操作结果。",
                "qa-and-gaps": "本节列出可执行验收标准和已解析缺口；页面只有在全部证据检查通过且缺口有明确结论后才能交付。",
            }
        else:
            prose = {
                "identity-and-evidence": "This section binds the page identity, approved status, route, and original design assets so every implementation decision remains traceable.",
                "canvas-shell-regions": "This section defines the native canvas, application shell, and complete region boundaries, including dimensions, hierarchy, and scrolling behavior.",
                "layout-copy-icons-data": "This section records layout relationships, visible copy, icon meaning, and data shapes that must be implemented and visually verified item by item.",
                "components-interactions-responsive": "This section contracts component instances, interaction outcomes, and responsive variants so registered components reproduce every declared behavior accurately.",
                "qa-and-gaps": "This section lists executable acceptance criteria and resolved gaps; delivery is allowed only when all bound evidence checks pass without ambiguity.",
            }
        section_values = {
            "identity-and-evidence": [
                identity,
                *page["sourceAssetIds"],
                page["route"]["path"],
            ],
            "canvas-shell-regions": [
                page["shell"]["shellId"],
                *(region["regionId"] for region in page["regions"]),
            ],
            "layout-copy-icons-data": [
                *(item["relationshipId"] for item in page["layoutRelationships"]),
                *(item["copyId"] for item in page["copy"]),
                *(item["text"][locale_code] for item in page["copy"]),
                *(item["iconId"] for item in page["icons"]),
                *(item["dataId"] for item in page["data"]),
                *(item["valueShape"] for item in page["data"]),
            ],
            "components-interactions-responsive": [
                *(item["instanceId"] for item in page["components"]),
                *(item["componentId"] for item in page["components"]),
                *(
                    component_names[item["componentId"]][locale_code]
                    for item in page["components"]
                ),
                *(item["interactionId"] for item in page["interactions"]),
                *(item["outcome"][locale_code] for item in page["interactions"]),
                *(item["responsiveVariantId"] for item in page["responsiveVariants"]),
            ],
            "qa-and-gaps": [
                *(item["qaId"] for item in page["acceptanceCriteria"]),
                *page["gapIds"],
            ],
        }
        for field in ("layoutRelationships", "copy", "icons", "data"):
            if not page[field]:
                section_values["layout-copy-icons-data"].append(f"[absence:{field}]")
        for field in ("components", "interactions"):
            if not page[field]:
                section_values["components-interactions-responsive"].append(
                    f"[absence:{field}]"
                )
        lines = [
            "---",
            "templateId: page-contract",
            f"locale: {locale_code}",
            "---",
            "",
            f"# Page Contract: {identity}",
            "",
        ]
        for section_id, values in section_values.items():
            body = " ".join(f"`{value}`" for value in values)
            if section_id == "identity-and-evidence":
                body += f" [design](../../../{source_link})"
            lines.extend(
                [
                    f"sectionId: {section_id}",
                    f"contractHash: {_contract_hash(page, section_id)}",
                    "",
                    f"## {section_id}",
                    "",
                    prose[section_id],
                    "",
                    body,
                    "",
                ]
            )
        path.write_text("\n".join(lines), encoding="utf-8")


def _create_directory_link(link, target):
    try:
        link.symlink_to(target, target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError):
        if os.name != "nt":
            raise
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise OSError(completed.stderr or completed.stdout)
    return "junction"


def _remove_directory_link(link, link_kind):
    if not os.path.lexists(link):
        return
    if link_kind == "junction":
        os.rmdir(link)
    else:
        link.unlink()


def _refresh_design_lock(handoff):
    lock_path = handoff / "contracts" / "design-lock.json"
    lock = _read_json(lock_path)
    ignored = {
        "contracts/design-lock.json",
        "reports/contact-sheet.png",
        "reports/validation-report.json",
    }
    files = [
        {
            "relativePath": path.relative_to(handoff).as_posix(),
            "sha256": _sha256(path),
        }
        for path in sorted(handoff.rglob("*"))
        if path.is_file() and path.relative_to(handoff).as_posix() not in ignored
    ]
    contract_records = [
        (entry["relativePath"], entry["sha256"])
        for entry in files
        if entry["relativePath"].startswith("contracts/")
    ]
    lock["files"] = files
    lock["contractsHash"] = _record_set_hash(contract_records)
    _write_json(lock_path, lock)


def _write_passing_qa_evidence(handoff, row, page, requirement_id, mapping):
    qa_root = f"reports/qa/{row['qaId']}"
    artifact_paths = {
        "reference": row["referencePath"],
        "current": f"{qa_root}/current.png",
        "overlay": f"{qa_root}/overlay.png",
        "diff": f"{qa_root}/diff.png",
    }
    source_reference = Image.open(handoff / artifact_paths["reference"]).convert("RGBA")
    images = {
        "reference": source_reference,
        "current": source_reference.copy(),
    }
    images["overlay"] = Image.blend(images["reference"], images["current"], 0.5)
    images["diff"] = ImageChops.difference(
        images["reference"], images["current"]
    )
    for name, image in images.items():
        if name == "reference":
            continue
        target = handoff / artifact_paths[name]
        target.parent.mkdir(parents=True, exist_ok=True)
        if name == "current":
            target.write_bytes((handoff / artifact_paths["reference"]).read_bytes())
        elif name == "overlay" and images["reference"].tobytes() == images[
            "current"
        ].tobytes():
            target.write_bytes((handoff / artifact_paths["reference"]).read_bytes())
        else:
            image.save(target, format="PNG")

    if row["evidenceType"] == "visual":
        checks = [
            {
                "checkType": "pixel-diff",
                "status": "pass",
                "actualPixelRatio": 0.0,
            }
        ]
    elif row["evidenceType"] == "structural":
        checks = [
            {
                "checkType": "requirement-map",
                "status": "pass",
                "requirementId": requirement_id,
            },
        ]
        checks.extend(
            {
                "checkType": "region-map",
                "status": "pass",
                "regionId": region["regionId"],
            }
            for region in page["regions"]
        )
        checks.extend(
            {
                "checkType": "component-map",
                "status": "pass",
                "instanceId": component["instanceId"],
                "componentId": component["componentId"],
            }
            for component in page["components"]
        )
    else:
        checks = [
            {
                "checkType": "interaction-case",
                "status": "pass",
                "interactionId": page["interactions"][0]["interactionId"],
            }
        ]

    runner = {
        "qaId": row["qaId"],
        "pageId": row["pageId"],
        "stateId": row["stateId"],
        "variantId": row["variantId"],
        "evidenceType": row["evidenceType"],
        "tool": "fixture-runner",
        "version": "1.0.0",
        "command": "fixture-runner --replay structured-input.json",
        "exitCode": 0,
        "startedAt": "2026-08-04T10:00:00Z",
        "finishedAt": "2026-08-04T10:00:01Z",
        "assertions": checks,
        "artifacts": {},
    }
    if row["evidenceType"] == "visual":
        runner.update(
            {
                "route": page["route"]["path"],
                "captureProfileId": row["captureProfileId"],
            }
        )
        runner["artifacts"]["current"] = {
            "path": artifact_paths["current"],
            "sha256": _sha256(handoff / artifact_paths["current"]),
        }
    elif row["evidenceType"] == "structural":
        dom_path = f"{qa_root}/dom-snapshot.json"
        dom_snapshot = {
            "pageId": row["pageId"],
            "stateId": row["stateId"],
            "variantId": row["variantId"],
            "nodes": [
                *(
                    {
                        "nodeId": f"node-region-{region['regionId']}",
                        "nodeType": "region",
                        "regionId": region["regionId"],
                    }
                    for region in page["regions"]
                ),
                *(
                    {
                        "nodeId": f"node-component-{component['instanceId']}",
                        "nodeType": "component",
                        "regionId": component["regionId"],
                        "instanceId": component["instanceId"],
                        "componentId": component["componentId"],
                    }
                    for component in page["components"]
                ),
            ],
        }
        _write_json(handoff / dom_path, dom_snapshot)
        implementation_path = f"{qa_root}/implementation-snapshot.json"
        implementation_snapshot = {
            "pageId": row["pageId"],
            "stateId": row["stateId"],
            "variantId": row["variantId"],
            "entries": [
                {
                    "targetFile": target_file,
                    "sha256": _sha256(handoff / target_file),
                }
                for target_file in mapping["targetFiles"]
            ],
            "regionMappings": mapping["regionMappings"],
            "componentMappings": mapping["componentMappings"],
        }
        _write_json(handoff / implementation_path, implementation_snapshot)
        runner["artifacts"].update(
            {
                "domSnapshot": {
                    "path": dom_path,
                    "sha256": _sha256(handoff / dom_path),
                },
                "implementationSnapshot": {
                    "path": implementation_path,
                    "sha256": _sha256(handoff / implementation_path),
                },
            }
        )
        runner["requirementMappings"] = [requirement_id]
    else:
        test_cases = [
            {
                "testCaseId": f"case-{interaction['interactionId']}",
                "interactionId": interaction["interactionId"],
                "status": "pass",
                "assertions": [
                    {
                        "assertionId": f"assert-{interaction['interactionId']}",
                        "status": "pass",
                    }
                ],
            }
            for interaction in page["interactions"]
        ]
        result_path = f"{qa_root}/interaction-result.json"
        _write_json(
            handoff / result_path,
            {
                "pageId": row["pageId"],
                "stateId": row["stateId"],
                "variantId": row["variantId"],
                "testCases": test_cases,
            },
        )
        runner["testCases"] = test_cases
        runner["artifacts"]["interactionResult"] = {
            "path": result_path,
            "sha256": _sha256(handoff / result_path),
        }
    runner_path = f"{qa_root}/runner-result.json"
    _write_json(handoff / runner_path, runner)

    record = {
        "qaId": row["qaId"],
        "pageId": row["pageId"],
        "stateId": row["stateId"],
        "variantId": row["variantId"],
        "evidenceType": row["evidenceType"],
        "status": "pass",
        "tool": "fixture-evidence-runner",
        "command": "python -m unittest tests.test_validate_handoff",
        "checks": checks,
        "runnerResultPath": runner_path,
        "runnerResultSha256": _sha256(handoff / runner_path),
        "artifacts": {
            name: {"path": path, "sha256": _sha256(handoff / path)}
            for name, path in artifact_paths.items()
        },
    }
    evidence_path = f"{qa_root}/evidence.json"
    _write_json(handoff / evidence_path, record)
    row.update(
        {
            "referencePath": artifact_paths["reference"],
            "currentPath": artifact_paths["current"],
            "overlayPath": artifact_paths["overlay"],
            "diffPath": artifact_paths["diff"],
            "evidenceRecordPath": evidence_path,
            "evidenceRecordSha256": _sha256(handoff / evidence_path),
            "status": "pass",
        }
    )


def _rewrite_runner(handoff, evidence_type, mutate):
    qa_path = handoff / "contracts" / "visual-qa-matrix.csv"
    rows = _read_csv(qa_path)
    row = next(item for item in rows if item["evidenceType"] == evidence_type)
    record_path = handoff / row["evidenceRecordPath"]
    record = _read_json(record_path)
    runner_path = handoff / record["runnerResultPath"]
    runner = _read_json(runner_path)
    mutate(runner, record, row)
    _write_json(runner_path, runner)
    record["runnerResultSha256"] = _sha256(runner_path)
    _write_json(record_path, record)
    row["evidenceRecordSha256"] = _sha256(record_path)
    _write_csv(qa_path, rows, list(rows[0]))
    _refresh_design_lock(handoff)
    return row, record, runner


def _rewrite_structural_bundle(handoff, mutate):
    def update(runner, record, row):
        dom_metadata = runner["artifacts"]["domSnapshot"]
        implementation_metadata = runner["artifacts"]["implementationSnapshot"]
        dom_path = handoff / dom_metadata["path"]
        implementation_path = handoff / implementation_metadata["path"]
        dom = _read_json(dom_path)
        implementation = _read_json(implementation_path)
        mutate(runner, record, row, dom, implementation)
        _write_json(dom_path, dom)
        _write_json(implementation_path, implementation)
        dom_metadata["sha256"] = _sha256(dom_path)
        implementation_metadata["sha256"] = _sha256(implementation_path)

    return _rewrite_runner(handoff, "structural", update)


def _rewrite_page_section(path, section_id, transform):
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(?ms)(^sectionId:\s*{re.escape(section_id)}\s*$)(.*?)(?=^sectionId:|\Z)"
    )
    match = pattern.search(text)
    if match is None:
        raise AssertionError(f"missing section {section_id} in {path}")
    body = transform(match.group(2))
    path.write_text(
        text[: match.start()] + match.group(1) + body + text[match.end() :],
        encoding="utf-8",
    )


def _resolve_generated_skeleton(handoff):
    page_inventory_path = handoff / "contracts" / "page-inventory.json"
    page_inventory = _read_json(page_inventory_path)
    for number, page in enumerate(page_inventory["pages"], start=1):
        component_id = f"component-{page['pageId']}-card"
        interaction_id = f"interaction-{page['pageId']}-open"
        page["route"].update(
            {"path": f"/page-{number}", "evidenceLevel": "direct", "gapId": None}
        )
        page["shell"].update(
            {"shellId": "app-shell", "evidenceLevel": "direct", "gapId": None}
        )
        for region in page["regions"]:
            region.update({"role": "content", "evidenceLevel": "direct", "gapIds": []})
        for criterion in page["acceptanceCriteria"]:
            criterion["status"] = "pass"
        page.update(
            {
                "layoutRelationships": [
                    {
                        "relationshipId": f"layout-{page['pageId']}",
                        "containerId": "region-canvas",
                        "display": "block",
                        "relation": "contains",
                        "targetIds": [component_id],
                        "ratio": None,
                        "gap": 0,
                        "minSize": 0,
                        "overflow": "visible",
                        "evidenceLevel": "approved",
                        "gapIds": [],
                    }
                ],
                "copy": [
                    {
                        "copyId": f"copy-{page['pageId']}-title",
                        "text": {"zh-CN": "示例标题", "en-US": "Sample title"},
                        "classification": "verified",
                        "evidenceLevel": "approved",
                        "sourceBounds": {"x": 0, "y": 0, "width": 8, "height": 6},
                        "gapId": None,
                    }
                ],
                "icons": [
                    {
                        "iconId": f"icon-{page['pageId']}-sample",
                        "assetId": page["sourceAssetIds"][0],
                        "meaning": {"zh-CN": "示例图标", "en-US": "Sample icon"},
                        "evidenceLevel": "approved",
                        "gapId": None,
                    }
                ],
                "components": [
                    {
                        "instanceId": f"instance-{page['pageId']}-card",
                        "componentId": component_id,
                        "regionId": "region-canvas",
                        "evidenceLevel": "approved",
                        "gapId": None,
                    }
                ],
                "data": [
                    {
                        "dataId": f"data-{page['pageId']}-sample",
                        "classification": "verified",
                        "valueShape": "localized-title",
                        "sourceRef": page["sourceAssetIds"][0],
                        "evidenceLevel": "approved",
                        "gapId": None,
                    }
                ],
                "interactions": [
                    {
                        "interactionId": interaction_id,
                        "trigger": "click",
                        "outcome": {"zh-CN": "打开详情", "en-US": "Open details"},
                        "status": "approved",
                        "evidenceLevel": "approved",
                        "gapId": None,
                    }
                ],
                "status": "approved",
                "gapIds": [],
            }
        )
    _write_json(page_inventory_path, page_inventory)

    registry_path = handoff / "contracts" / "component-registry.json"
    registry = _read_json(registry_path)
    registry["components"] = [
        {
            "componentId": f"component-{page['pageId']}-card",
            "name": {"zh-CN": "示例卡片", "en-US": "Sample card"},
            "status": "approved",
            "evidenceLevel": "approved",
            "sourcePageIdentities": [
                {
                    "pageId": page["pageId"],
                    "stateId": page["stateId"],
                    "variantId": page["variantId"],
                }
            ],
            "anatomy": ["root"],
            "variants": [],
            "states": [],
            "props": [],
            "interactions": [],
            "styleTokenRefs": [],
            "gapIds": [],
        }
        for page in page_inventory["pages"]
    ]
    _write_json(registry_path, registry)

    style_path = handoff / "contracts" / "ui-style-contract.json"
    style = _read_json(style_path)
    style.update({"evidenceLevel": "approved", "status": "approved", "gapIds": []})
    for variant in style["responsiveVariants"]:
        variant.update(
            {"evidenceLevel": "approved", "status": "approved", "gapIds": []}
        )
    _write_json(style_path, style)

    implementation_path = handoff / "contracts" / "implementation-map.json"
    implementation = _read_json(implementation_path)
    for number, mapping in enumerate(implementation["mappings"], start=1):
        target = f"src/pages/page-{number}.py"
        target_path = handoff / target
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            f"# implementation for {mapping['pageId']}\n",
            encoding="utf-8",
        )
        page = page_inventory["pages"][number - 1]
        mapping.update(
            {
                "route": f"/page-{number}",
                "targetFiles": [target],
                "shellComponentId": "app-shell",
                "regionMappings": [
                    {
                        "regionId": page["regions"][0]["regionId"],
                        "targetSelector": "main",
                        "targetFile": target,
                        "evidenceLevel": "approved",
                        "gapIds": [],
                    }
                ],
                "componentMappings": [
                    {
                        "instanceId": page["components"][0]["instanceId"],
                        "componentId": page["components"][0]["componentId"],
                        "targetSymbol": "PageCard",
                        "targetFile": target,
                        "evidenceLevel": "approved",
                        "gapIds": [],
                    }
                ],
                "interactionMappings": [
                    {
                        "interactionId": page["interactions"][0]["interactionId"],
                        "targetHandler": "open_details",
                        "status": "approved",
                        "evidenceLevel": "approved",
                        "gapId": None,
                    }
                ],
                "evidenceLevel": "approved",
                "status": "approved",
                "gapIds": [],
            }
        )
        for responsive in mapping["responsiveMappings"]:
            responsive.update(
                {
                    "targetFiles": [target],
                    "evidenceLevel": "approved",
                    "status": "approved",
                    "gapIds": [],
                }
            )
    _write_json(implementation_path, implementation)

    mappings = {
        mapping["pageId"]: mapping for mapping in implementation["mappings"]
    }
    for page in page_inventory["pages"]:
        _write_complete_page_documents(handoff, page, registry)

    capture_path = handoff / "contracts" / "capture-profile.json"
    capture = _read_json(capture_path)
    for profile in capture["profiles"]:
        profile.update(
            {
                "browser": "Chromium",
                "browserVersion": "120",
                "locale": "en-US",
                "timezone": "UTC",
                "theme": "light",
                "fontEnvironment": ["Arial"],
                "evidenceLevel": "approved",
                "gapIds": [],
            }
        )
    _write_json(capture_path, capture)

    diff_path = handoff / "contracts" / "diff-regions.json"
    diff = _read_json(diff_path)
    for page in diff["pages"]:
        for region in page["regions"]:
            region["status"] = "pass"
    _write_json(diff_path, diff)

    qa_path = handoff / "contracts" / "visual-qa-matrix.csv"
    qa_rows = _read_csv(qa_path)
    requirements = {
        row["pageId"]: row["requirementId"]
        for row in _read_csv(handoff / "contracts" / "requirement-ledger.csv")
    }
    pages = {page["pageId"]: page for page in page_inventory["pages"]}
    for row in qa_rows:
        _write_passing_qa_evidence(
            handoff,
            row,
            pages[row["pageId"]],
            requirements[row["pageId"]],
            mappings[row["pageId"]],
        )
    _write_csv(qa_path, qa_rows, list(qa_rows[0]))

    gap_path = handoff / "contracts" / "gap-register.csv"
    gap_rows = _read_csv(gap_path)
    for row in gap_rows:
        row["status"] = "resolved"
        row["resolution"] = "Evidence reviewed for validation fixture"
    _write_csv(gap_path, gap_rows, list(gap_rows[0]))

    _write_image(handoff / "reports" / "contact-sheet.png", (64, 32), "white")
    _refresh_design_lock(handoff)


class ValidateHandoffTests(unittest.TestCase):
    def test_locale_word_frequency_check_is_linear_time(self):
        validator_source = VALIDATE_PATH.read_text(encoding="utf-8")

        self.assertIn("Counter(words).most_common(1)", validator_source)
        self.assertNotIn("words.count(", validator_source)

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "source"
        self.handoff = self.root / "allowed" / "handoff"
        _write_image(self.source / "screen.png")
        PREPARE.prepare_handoff(self.source, self.handoff, "v1")
        _resolve_generated_skeleton(self.handoff)

    def validate(self, **kwargs):
        validator = _load_module(VALIDATE_PATH, "validate_handoff")
        return validator.validate_handoff(self.handoff, **kwargs)

    def codes(self, result):
        return {issue["code"] for issue in result["issues"]}

    def assert_absence_marker_accepted(self, field, section_id, id_fields):
        inventory_path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(inventory_path)
        page = inventory["pages"][0]
        removed_ids = [
            item[id_field]
            for item in page[field]
            for id_field in id_fields
            if id_field in item
        ]
        page[field] = []
        page["gapIds"] = ["G001"]
        _write_json(inventory_path, inventory)
        gap_path = self.handoff / "contracts" / "gap-register.csv"
        gaps = _read_csv(gap_path)
        gaps[0]["status"] = "resolved"
        gaps[0]["resolution"] = f"Reviewed visual evidence [absence:{field}]"
        _write_csv(gap_path, gaps, list(gaps[0]))
        implementation_path = self.handoff / "contracts" / "implementation-map.json"
        implementation = _read_json(implementation_path)
        mapping = implementation["mappings"][0]
        if field == "components":
            mapping["componentMappings"] = []
        elif field == "interactions":
            mapping["interactionMappings"] = []
        _write_json(implementation_path, implementation)

        registry = _read_json(self.handoff / "contracts" / "component-registry.json")
        _write_complete_page_documents(self.handoff, page, registry)

        if field == "components":
            def remove_components(runner, record, _row, dom, implementation_snapshot):
                absence = {
                    "checkType": "absence-check",
                    "field": "components",
                    "gapId": "G001",
                    "actualInstanceIds": [],
                    "actualComponentIds": [],
                    "status": "pass",
                }
                runner["assertions"] = [
                    assertion
                    for assertion in runner["assertions"]
                    if assertion["checkType"] != "component-map"
                ] + [absence]
                record["checks"] = [
                    check
                    for check in record["checks"]
                    if check["checkType"] != "component-map"
                ] + [absence]
                dom["nodes"] = [
                    node for node in dom["nodes"] if node["nodeType"] != "component"
                ]
                implementation_snapshot["componentMappings"] = []

            _rewrite_structural_bundle(self.handoff, remove_components)
        elif field == "interactions":
            def remove_interactions(runner, record, _row):
                absence = {
                    "checkType": "absence-check",
                    "field": "interactions",
                    "gapId": "G001",
                    "actualInteractionIds": [],
                    "actualCaseCount": 0,
                    "status": "pass",
                }
                runner["assertions"] = [absence]
                record["checks"] = [absence]
                runner["testCases"] = []
                result_metadata = runner["artifacts"]["interactionResult"]
                result_path = self.handoff / result_metadata["path"]
                result = _read_json(result_path)
                result["testCases"] = []
                _write_json(result_path, result)
                result_metadata["sha256"] = _sha256(result_path)

            _rewrite_runner(self.handoff, "interaction", remove_interactions)
        _refresh_design_lock(self.handoff)

        result = self.validate(source_root=self.source)
        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["issues"], [])

    def test_accepts_complete_package_and_exposes_computed_lock_material(self):
        result = self.validate(source_root=self.source)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["issues"], [])
        lock = _read_json(self.handoff / "contracts" / "design-lock.json")
        self.assertEqual(
            result["designLock"]["computedContractsHash"], lock["contractsHash"]
        )
        self.assertEqual(result["designLock"]["computedFileCount"], len(lock["files"]))
        persisted = _read_json(self.handoff / "reports" / "validation-report.json")
        self.assertEqual(persisted, result)

    def test_source_verification_is_required_for_readiness(self):
        result = self.validate()

        self.assertEqual(result["status"], "failed")
        self.assertIn("SOURCE_VERIFICATION_REQUIRED", self.codes(result))

    def test_reports_blank_markdown_and_unresolved_template_placeholder(self):
        readme = self.handoff / "README.md"
        readme.write_text("   \n", encoding="utf-8")
        page = next((self.handoff / "docs" / "en" / "pages").glob("*.md"))
        page.write_text(
            page.read_text(encoding="utf-8") + "\n{{unresolved-copy}}\n",
            encoding="utf-8",
        )
        _refresh_design_lock(self.handoff)

        codes = self.codes(self.validate(source_root=self.source))

        self.assertIn("EMPTY_MARKDOWN", codes)
        self.assertIn("UNRESOLVED_MARKDOWN_PLACEHOLDER", codes)

    def test_reports_missing_page_section_and_machine_identifier(self):
        page = next((self.handoff / "docs" / "en" / "pages").glob("*.md"))
        text = page.read_text(encoding="utf-8")
        text = text.replace("sectionId: qa-and-gaps", "sectionId: removed")
        text = text.replace("component-P001-card", "component-omitted")
        page.write_text(text, encoding="utf-8")
        _refresh_design_lock(self.handoff)

        codes = self.codes(self.validate(source_root=self.source))

        self.assertIn("PAGE_DOCUMENT_SECTION_MISSING", codes)
        self.assertIn("PAGE_DOCUMENT_REFERENCE_MISSING", codes)

    def test_machine_identifier_in_the_wrong_page_section_fails(self):
        page = next((self.handoff / "docs" / "en" / "pages").glob("*.md"))
        component_id = "component-P001-card"
        _rewrite_page_section(
            page,
            "components-interactions-responsive",
            lambda body: body.replace(f"`{component_id}`", ""),
        )
        _rewrite_page_section(
            page,
            "qa-and-gaps",
            lambda body: body + f"\n`{component_id}`\n",
        )
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "PAGE_DOCUMENT_SECTION_REFERENCE_MISSING",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_approved_page_requires_correct_contract_hash_in_every_section(self):
        page = _read_json(self.handoff / "contracts" / "page-inventory.json")["pages"][0]
        identity = f"{page['pageId']}-{page['stateId']}-{page['variantId']}"
        document = next((self.handoff / "docs" / "en" / "pages").glob(f"{identity}-*.md"))
        _rewrite_page_section(
            document,
            "canvas-shell-regions",
            lambda body: re.sub(
                r"contractHash:\s*sha256:[0-9a-f]{64}",
                "contractHash: sha256:" + "0" * 64,
                body,
            ),
        )
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "PAGE_DOCUMENT_CONTRACT_HASH_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_approved_page_section_requires_meaningful_locale_prose(self):
        page = _read_json(self.handoff / "contracts" / "page-inventory.json")["pages"][0]
        identity = f"{page['pageId']}-{page['stateId']}-{page['variantId']}"
        document = next((self.handoff / "docs" / "en" / "pages").glob(f"{identity}-*.md"))

        def remove_prose(body):
            return "\n".join(
                line
                for line in body.splitlines()
                if "contractHash:" in line or "`" in line or line.startswith("##")
            ) + "\n"

        _rewrite_page_section(document, "layout-copy-icons-data", remove_prose)
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "PAGE_DOCUMENT_SECTION_PROSE_INSUFFICIENT",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_approved_page_section_rejects_repeated_low_entropy_prose(self):
        page = _read_json(self.handoff / "contracts" / "page-inventory.json")["pages"][0]
        identity = f"{page['pageId']}-{page['stateId']}-{page['variantId']}"
        for locale in ("zh", "en"):
            document = next(
                (self.handoff / "docs" / locale / "pages").glob(f"{identity}-*.md")
            )

            def replace_prose(body):
                lines = body.splitlines()
                for index, line in enumerate(lines):
                    if line and not line.startswith(("#", "sectionId:", "contractHash:")) and "`" not in line:
                        lines[index] = "a" * 50
                        break
                return "\n".join(lines) + "\n"

            _rewrite_page_section(document, "layout-copy-icons-data", replace_prose)
        _refresh_design_lock(self.handoff)

        result = self.validate(source_root=self.source)

        self.assertIn("PAGE_DOCUMENT_SECTION_PROSE_INSUFFICIENT", self.codes(result))
        prose_issues = [
            issue
            for issue in result["issues"]
            if issue["code"] == "PAGE_DOCUMENT_SECTION_PROSE_INSUFFICIENT"
            and issue.get("sectionId") == "layout-copy-icons-data"
        ]
        self.assertSetEqual({issue.get("locale") for issue in prose_issues}, {"zh-CN", "en-US"})

    def test_approved_page_section_rejects_wrong_locale_prose(self):
        page = _read_json(self.handoff / "contracts" / "page-inventory.json")["pages"][0]
        identity = f"{page['pageId']}-{page['stateId']}-{page['variantId']}"
        replacements = {
            "zh": "This English sentence has many distinct words but does not satisfy Chinese locale prose requirements.",
            "en": "这段中文说明包含足够多的不同汉字但是不能满足英文语言环境的文档说明要求。",
        }
        for locale, replacement in replacements.items():
            document = next(
                (self.handoff / "docs" / locale / "pages").glob(f"{identity}-*.md")
            )

            def replace_prose(body, replacement=replacement):
                lines = body.splitlines()
                for index, line in enumerate(lines):
                    if line and not line.startswith(("#", "sectionId:", "contractHash:")) and "`" not in line:
                        lines[index] = replacement
                        break
                return "\n".join(lines) + "\n"

            _rewrite_page_section(document, "layout-copy-icons-data", replace_prose)
        _refresh_design_lock(self.handoff)

        result = self.validate(source_root=self.source)

        prose_issues = [
            issue
            for issue in result["issues"]
            if issue["code"] == "PAGE_DOCUMENT_SECTION_PROSE_INSUFFICIENT"
            and issue.get("sectionId") == "layout-copy-icons-data"
        ]
        self.assertSetEqual({issue.get("locale") for issue in prose_issues}, {"zh-CN", "en-US"})

    def test_page_document_requires_localized_copy_and_value_shape(self):
        page = _read_json(self.handoff / "contracts" / "page-inventory.json")["pages"][0]
        identity = f"{page['pageId']}-{page['stateId']}-{page['variantId']}"
        document = next((self.handoff / "docs" / "en" / "pages").glob(f"{identity}-*.md"))
        _rewrite_page_section(
            document,
            "layout-copy-icons-data",
            lambda body: body.replace("`Sample title`", "").replace("`localized-title`", ""),
        )
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "PAGE_DOCUMENT_LOCALIZED_CONTENT_MISSING",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_page_document_requires_localized_behavior_names_and_outcomes(self):
        page = _read_json(self.handoff / "contracts" / "page-inventory.json")["pages"][0]
        identity = f"{page['pageId']}-{page['stateId']}-{page['variantId']}"
        document = next((self.handoff / "docs" / "en" / "pages").glob(f"{identity}-*.md"))
        _rewrite_page_section(
            document,
            "components-interactions-responsive",
            lambda body: body.replace("`Sample card`", "").replace("`Open details`", ""),
        )
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "PAGE_DOCUMENT_LOCALIZED_CONTENT_MISSING",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_structural_dom_requires_exact_typed_region_and_component_coverage(self):
        def mutate(_runner, _record, _row, dom, _implementation):
            dom["nodes"].append(
                {"nodeId": "extra-region", "nodeType": "region", "regionId": "region-extra"}
            )

        _rewrite_structural_bundle(self.handoff, mutate)

        self.assertIn(
            "QA_STRUCTURAL_DOM_COVERAGE_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_structural_implementation_snapshot_rejects_duplicate_mapping(self):
        def mutate(_runner, _record, _row, _dom, implementation):
            implementation["regionMappings"].append(dict(implementation["regionMappings"][0]))

        _rewrite_structural_bundle(self.handoff, mutate)

        self.assertIn(
            "QA_STRUCTURAL_IMPLEMENTATION_MAPPING_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_structural_corrupt_mapping_shapes_fail_closed_without_crashing(self):
        def mutate(runner, _record, _row, dom, implementation):
            dom["nodes"][0]["regionId"] = {"forged": True}
            implementation["regionMappings"][0]["regionId"] = {"forged": True}
            runner["requirementMappings"] = [{"forged": True}]

        _rewrite_structural_bundle(self.handoff, mutate)

        result = self.validate(source_root=self.source)
        codes = self.codes(result)

        self.assertEqual(result["status"], "failed")
        self.assertIn("QA_STRUCTURAL_DOM_COVERAGE_MISMATCH", codes)
        self.assertIn("QA_STRUCTURAL_IMPLEMENTATION_MAPPING_MISMATCH", codes)
        self.assertIn("QA_STRUCTURAL_REQUIREMENT_COVERAGE_MISMATCH", codes)

    def test_structural_runner_requires_exact_requirement_and_assertion_coverage(self):
        def mutate(runner, _record, _row):
            runner["requirementMappings"].append("R999")
            runner["assertions"] = [
                assertion
                for assertion in runner["assertions"]
                if assertion["checkType"] != "region-map"
            ]

        _rewrite_runner(self.handoff, "structural", mutate)
        codes = self.codes(self.validate(source_root=self.source))

        self.assertIn("QA_STRUCTURAL_REQUIREMENT_COVERAGE_MISMATCH", codes)
        self.assertIn("QA_STRUCTURAL_RUNNER_ASSERTIONS_INVALID", codes)

    def test_approved_implementation_map_rejects_missing_region_mapping(self):
        path = self.handoff / "contracts" / "implementation-map.json"
        implementation = _read_json(path)
        implementation["mappings"][0]["regionMappings"] = []
        _write_json(path, implementation)
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "IMPLEMENTATION_MAPPING_COVERAGE_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_approved_implementation_map_rejects_duplicate_component_mapping(self):
        path = self.handoff / "contracts" / "implementation-map.json"
        implementation = _read_json(path)
        component_mapping = implementation["mappings"][0]["componentMappings"][0]
        implementation["mappings"][0]["componentMappings"].append(
            dict(component_mapping)
        )
        _write_json(path, implementation)
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "IMPLEMENTATION_MAPPING_COVERAGE_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_structural_assertions_reject_duplicate_entity(self):
        def mutate(runner, record, _row):
            runner["assertions"].append(dict(runner["assertions"][0]))
            record["checks"].append(dict(record["checks"][0]))

        _rewrite_runner(self.handoff, "structural", mutate)
        codes = self.codes(self.validate(source_root=self.source))

        self.assertIn("QA_STRUCTURAL_RUNNER_ASSERTIONS_INVALID", codes)
        self.assertIn("QA_STRUCTURAL_CHECK_COVERAGE_MISSING", codes)

    def test_reports_approved_page_with_empty_substantive_contract(self):
        path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(path)
        for field in (
            "layoutRelationships",
            "copy",
            "components",
            "data",
            "interactions",
        ):
            inventory["pages"][0][field] = []
        _write_json(path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "APPROVED_PAGE_SUBSTANTIVE_FIELD_EMPTY",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_approved_page_without_icons_or_resolved_absence_gap(self):
        path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(path)
        inventory["pages"][0]["icons"] = []
        _write_json(path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "APPROVED_PAGE_SUBSTANTIVE_FIELD_EMPTY",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_allows_empty_icons_with_resolved_explicit_absence_gap(self):
        self.assert_absence_marker_accepted(
            "icons", "layout-copy-icons-data", ("iconId",)
        )

    def test_allows_empty_layout_with_resolved_explicit_absence_gap(self):
        self.assert_absence_marker_accepted(
            "layoutRelationships",
            "layout-copy-icons-data",
            ("relationshipId",),
        )

    def test_allows_empty_copy_with_resolved_explicit_absence_gap(self):
        self.assert_absence_marker_accepted(
            "copy", "layout-copy-icons-data", ("copyId",)
        )

    def test_allows_empty_components_with_resolved_explicit_absence_gap(self):
        self.assert_absence_marker_accepted(
            "components",
            "components-interactions-responsive",
            ("instanceId", "componentId"),
        )

    def test_allows_empty_data_with_resolved_explicit_absence_gap(self):
        self.assert_absence_marker_accepted(
            "data", "layout-copy-icons-data", ("dataId",)
        )

    def test_allows_empty_interactions_with_resolved_explicit_absence_gap(self):
        self.assert_absence_marker_accepted(
            "interactions",
            "components-interactions-responsive",
            ("interactionId",),
        )

    def test_component_absence_requires_verified_runner_and_record_assertion(self):
        self.assert_absence_marker_accepted(
            "components",
            "components-interactions-responsive",
            ("instanceId", "componentId"),
        )

        def remove_absence(runner, record, _row):
            runner["assertions"] = [
                assertion
                for assertion in runner["assertions"]
                if assertion["checkType"] != "absence-check"
            ]
            record["checks"] = [
                check for check in record["checks"] if check["checkType"] != "absence-check"
            ]

        _rewrite_runner(self.handoff, "structural", remove_absence)
        codes = self.codes(self.validate(source_root=self.source))

        self.assertIn("QA_STRUCTURAL_RUNNER_ASSERTIONS_INVALID", codes)
        self.assertIn("QA_STRUCTURAL_CHECK_COVERAGE_MISSING", codes)

    def test_interaction_absence_requires_verified_zero_case_assertion(self):
        self.assert_absence_marker_accepted(
            "interactions",
            "components-interactions-responsive",
            ("interactionId",),
        )

        def remove_absence(runner, record, _row):
            runner["assertions"] = []
            record["checks"] = []

        _rewrite_runner(self.handoff, "interaction", remove_absence)
        codes = self.codes(self.validate(source_root=self.source))

        self.assertIn("QA_INTERACTION_TEST_CASES_INVALID", codes)
        self.assertIn("QA_INTERACTION_CHECK_REQUIRED", codes)

    def test_rejects_absence_marker_for_a_different_empty_field(self):
        inventory_path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(inventory_path)
        inventory["pages"][0]["copy"] = []
        inventory["pages"][0]["gapIds"] = ["G001"]
        _write_json(inventory_path, inventory)
        gap_path = self.handoff / "contracts" / "gap-register.csv"
        gaps = _read_csv(gap_path)
        gaps[0]["status"] = "resolved"
        gaps[0]["resolution"] = "Reviewed visual evidence [absence:icons]"
        _write_csv(gap_path, gaps, list(gaps[0]))
        _refresh_design_lock(self.handoff)

        issues = self.validate(source_root=self.source)["issues"]

        self.assertTrue(
            any(
                issue["code"] == "APPROVED_PAGE_SUBSTANTIVE_FIELD_EMPTY"
                and issue.get("field") == "copy"
                for issue in issues
            ),
            issues,
        )

    def test_reports_unresolved_page_component_and_empty_registry(self):
        registry_path = self.handoff / "contracts" / "component-registry.json"
        registry = _read_json(registry_path)
        registry["components"] = []
        _write_json(registry_path, registry)
        _refresh_design_lock(self.handoff)

        codes = self.codes(self.validate(source_root=self.source))

        self.assertIn("COMPONENT_REGISTRY_EMPTY", codes)
        self.assertIn("COMPONENT_ID_NOT_FOUND", codes)

    def test_completed_package_report_rerun_is_stable(self):
        first = self.validate(source_root=self.source)
        report_path = self.handoff / "reports" / "validation-report.json"
        first_bytes = report_path.read_bytes()

        second = self.validate(source_root=self.source)

        self.assertEqual(first["status"], "passed")
        self.assertEqual(_read_json(report_path), second)
        self.assertEqual(second, first)
        self.assertEqual(report_path.read_bytes(), first_bytes)

    def test_missing_validation_report_is_derived_and_rerun_stable(self):
        report_path = self.handoff / "reports" / "validation-report.json"
        report_path.unlink()

        first = self.validate(source_root=self.source)
        first_bytes = report_path.read_bytes()
        second = self.validate(source_root=self.source)

        self.assertEqual(first["status"], "passed")
        self.assertEqual(first, second)
        self.assertEqual(_read_json(report_path), second)
        self.assertEqual(report_path.read_bytes(), first_bytes)

    def test_malformed_validation_report_is_derived_and_rerun_stable(self):
        report_path = self.handoff / "reports" / "validation-report.json"
        report_path.write_text("{not-json", encoding="utf-8")

        first = self.validate(source_root=self.source)
        first_bytes = report_path.read_bytes()
        second = self.validate(source_root=self.source)

        self.assertEqual(first["status"], "passed")
        self.assertEqual(first, second)
        self.assertEqual(_read_json(report_path), second)
        self.assertEqual(report_path.read_bytes(), first_bytes)

    def test_legacy_lock_validation_report_entry_is_ignored_stably(self):
        report_path = self.handoff / "reports" / "validation-report.json"
        lock_path = self.handoff / "contracts" / "design-lock.json"
        lock = _read_json(lock_path)
        lock["files"].append(
            {
                "relativePath": "reports/validation-report.json",
                "sha256": _sha256(report_path),
            }
        )
        lock["files"].sort(key=lambda entry: entry["relativePath"])
        _write_json(lock_path, lock)
        lock_bytes = lock_path.read_bytes()

        first = self.validate(source_root=self.source)
        second = self.validate(source_root=self.source)

        self.assertEqual(first["status"], "passed")
        self.assertEqual(first, second)
        self.assertEqual(lock_path.read_bytes(), lock_bytes)
        self.assertNotIn("DESIGN_LOCK_FILE_HASH_MISMATCH", self.codes(second))
        self.assertNotIn("DESIGN_LOCK_FILE_SET_MISMATCH", self.codes(second))

    def test_validation_report_writer_rejects_linked_reports_directory(self):
        reports_path = self.handoff / "reports"
        outside_reports = self.root / "outside-reports"
        reports_path.rename(outside_reports)
        original_report = (outside_reports / "validation-report.json").read_bytes()
        try:
            link_kind = _create_directory_link(reports_path, outside_reports)
        except OSError as error:
            self.skipTest(f"directory links unavailable: {error}")
        self.addCleanup(_remove_directory_link, reports_path, link_kind)

        result = self.validate(source_root=self.source)

        self.assertEqual(result["status"], "failed")
        self.assertIn("VALIDATION_REPORT_UNSAFE_LAYOUT", self.codes(result))
        self.assertEqual(
            (outside_reports / "validation-report.json").read_bytes(),
            original_report,
        )
        self.assertEqual(
            list(outside_reports.glob(".validation-report-*.tmp")), []
        )

    def test_untouched_generated_package_fails_and_replaces_not_run_report(self):
        raw_handoff = self.root / "raw-handoff"
        PREPARE.prepare_handoff(self.source, raw_handoff, "v1")
        validator = _load_module(VALIDATE_PATH, "validate_raw_handoff")

        result = validator.validate_handoff(raw_handoff, source_root=self.source)

        self.assertEqual(result["status"], "failed")
        self.assertNotIn("VALIDATION_NOT_RUN", self.codes(result))
        self.assertEqual(
            _read_json(raw_handoff / "reports" / "validation-report.json"), result
        )

    def test_reports_missing_required_file(self):
        (self.handoff / "README.md").unlink()
        _refresh_design_lock(self.handoff)

        result = self.validate()

        self.assertEqual(result["status"], "failed")
        self.assertIn("MISSING_REQUIRED_FILE", self.codes(result))

    def test_empty_package_contracts_and_top_level_docs_fail_closed(self):
        collections = (
            ("asset-manifest.json", "assets"),
            ("page-inventory.json", "pages"),
            ("capture-profile.json", "profiles"),
            ("implementation-map.json", "mappings"),
            ("diff-regions.json", "pages"),
        )
        for filename, key in collections:
            path = self.handoff / "contracts" / filename
            document = _read_json(path)
            document[key] = []
            _write_json(path, document)
        qa_path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        qa_rows = _read_csv(qa_path)
        _write_csv(qa_path, [], list(qa_rows[0]))
        for relative_path in (
            "docs/zh/设计稿总目录.md",
            "docs/zh/UI实施说明.md",
            "docs/zh/组件规范.md",
            "docs/en/Design-Catalog.md",
            "docs/en/UI-Implementation-Guide.md",
            "docs/en/Component-Specification.md",
        ):
            (self.handoff / relative_path).unlink()
        _refresh_design_lock(self.handoff)

        codes = self.codes(self.validate())

        self.assertTrue(
            {
                "MISSING_REQUIRED_FILE",
                "EMPTY_ASSET_MANIFEST",
                "EMPTY_PAGE_INVENTORY",
                "EMPTY_CAPTURE_PROFILES",
                "EMPTY_IMPLEMENTATION_MAP",
                "EMPTY_DIFF_PAGES",
                "EMPTY_QA_MATRIX",
            }.issubset(codes),
            codes,
        )

    def test_reports_missing_implementation_mapping_for_page_identity(self):
        path = self.handoff / "contracts" / "implementation-map.json"
        implementation = _read_json(path)
        implementation["mappings"] = []
        _write_json(path, implementation)
        _refresh_design_lock(self.handoff)

        self.assertIn("MISSING_IMPLEMENTATION_MAPPING", self.codes(self.validate()))

    def test_reports_qa_capture_profile_that_does_not_exist(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["captureProfileId"] = "capture-missing"
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_CAPTURE_PROFILE_MISSING", self.codes(self.validate()))

    def test_reports_diff_capture_profile_that_does_not_exist(self):
        path = self.handoff / "contracts" / "diff-regions.json"
        diff = _read_json(path)
        diff["pages"][0]["captureProfileId"] = "capture-missing"
        _write_json(path, diff)
        _refresh_design_lock(self.handoff)

        self.assertIn("DIFF_CAPTURE_PROFILE_MISSING", self.codes(self.validate()))

    def test_reports_qa_capture_profile_mismatch_with_diff_page(self):
        capture_path = self.handoff / "contracts" / "capture-profile.json"
        capture = _read_json(capture_path)
        other = dict(capture["profiles"][0])
        other["captureProfileId"] = "capture-other"
        capture["profiles"].append(other)
        _write_json(capture_path, capture)
        qa_path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(qa_path)
        rows[0]["captureProfileId"] = "capture-other"
        _write_csv(qa_path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_DIFF_CAPTURE_PROFILE_MISMATCH", self.codes(self.validate()))

    def test_reports_qa_region_missing_from_diff_page(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["regionId"] = "region-missing"
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_REGION_MISSING", self.codes(self.validate()))

    def test_reports_qa_row_for_unknown_page_identity(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        orphan = dict(rows[0])
        orphan.update({"qaId": "QA999", "pageId": "P999"})
        rows.append(orphan)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_TARGET_IDENTITY_MISSING", self.codes(self.validate()))

    def test_reports_reused_qa_evidence_path(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["currentPath"] = rows[0]["referencePath"]
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_EVIDENCE_PATH_REUSED", self.codes(self.validate()))

    def test_allows_distinct_qa_paths_with_identical_content_hashes(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        visual = next(row for row in rows if row["evidenceType"] == "visual")
        repeated_hashes = {
            _sha256(self.handoff / visual[field])
            for field in ("referencePath", "currentPath", "overlayPath")
        }

        result = self.validate(source_root=self.source)

        self.assertEqual(len(repeated_hashes), 1)
        self.assertEqual(result["status"], "passed")
        self.assertNotIn("QA_EVIDENCE_HASH_REUSED", self.codes(result))

    def test_passed_qa_row_requires_hashed_evidence_record(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["evidenceRecordPath"] = ""
        rows[0]["evidenceRecordSha256"] = ""
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_EVIDENCE_RECORD_REQUIRED",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_unsafe_qa_evidence_record_path(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["evidenceRecordPath"] = "../outside.json"
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_EVIDENCE_RECORD_PATH_UNSAFE",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_qa_evidence_record_hash_mismatch(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["evidenceRecordSha256"] = "0" * 64
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_EVIDENCE_RECORD_HASH_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_malformed_qa_evidence_record(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        record_path = self.handoff / rows[0]["evidenceRecordPath"]
        record_path.write_text("{not-json", encoding="utf-8")
        rows[0]["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_EVIDENCE_RECORD_INVALID_JSON",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_qa_evidence_record_identity_mismatch(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        record_path = self.handoff / rows[0]["evidenceRecordPath"]
        record = _read_json(record_path)
        record["qaId"] = "QA999"
        _write_json(record_path, record)
        rows[0]["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_EVIDENCE_RECORD_FIELD_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_qa_evidence_record_with_nonpassing_check(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        record_path = self.handoff / rows[0]["evidenceRecordPath"]
        record = _read_json(record_path)
        record["checks"][0]["status"] = "fail"
        _write_json(record_path, record)
        rows[0]["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_EVIDENCE_CHECK_NOT_PASSED",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_visual_reference_must_be_the_page_manifest_asset(self):
        qa_path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(qa_path)
        visual = next(row for row in rows if row["evidenceType"] == "visual")
        copied_reference = "reports/qa/copied-reference.png"
        target = self.handoff / copied_reference
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((self.handoff / visual["referencePath"]).read_bytes())
        record_path = self.handoff / visual["evidenceRecordPath"]
        record = _read_json(record_path)
        record["artifacts"]["reference"] = {
            "path": copied_reference,
            "sha256": _sha256(target),
        }
        visual["referencePath"] = copied_reference
        _write_json(record_path, record)
        visual["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(qa_path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_VISUAL_REFERENCE_NOT_MANIFEST_ASSET",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_visual_reference_dimensions_must_match_canvas_and_full_region(self):
        inventory_path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(inventory_path)
        inventory["pages"][0]["canvas"]["width"] -= 1
        _write_json(inventory_path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_VISUAL_REFERENCE_DIMENSION_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_copied_current_capture_cannot_pass_without_runner_result(self):
        qa_path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(qa_path)
        visual = next(row for row in rows if row["evidenceType"] == "visual")
        record_path = self.handoff / visual["evidenceRecordPath"]
        record = _read_json(record_path)
        record.pop("runnerResultPath")
        record.pop("runnerResultSha256")
        _write_json(record_path, record)
        visual["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(qa_path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_RUNNER_RESULT_REQUIRED",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_bad_runner_result_hash(self):
        qa_path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(qa_path)
        visual = next(row for row in rows if row["evidenceType"] == "visual")
        record_path = self.handoff / visual["evidenceRecordPath"]
        record = _read_json(record_path)
        record["runnerResultSha256"] = "0" * 64
        _write_json(record_path, record)
        visual["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(qa_path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_RUNNER_RESULT_HASH_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_runner_result_requires_zero_exit_and_passing_assertions(self):
        def mutate(runner, _record, _row):
            runner["exitCode"] = 1
            runner["assertions"][0]["status"] = "fail"

        _rewrite_runner(self.handoff, "visual", mutate)
        codes = self.codes(self.validate(source_root=self.source))

        self.assertIn("QA_RUNNER_EXECUTION_INVALID", codes)
        self.assertIn("QA_RUNNER_ASSERTION_NOT_PASSED", codes)

    def test_validator_never_executes_runner_command_text(self):
        sentinel = self.root / "runner-command-executed.txt"

        def mutate(runner, _record, _row):
            runner["command"] = (
                f'python -c "from pathlib import Path; '
                f"Path(r'{sentinel}').write_text('unsafe')\""
            )

        _rewrite_runner(self.handoff, "visual", mutate)

        result = self.validate(source_root=self.source)

        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertFalse(sentinel.exists())

    def test_visual_runner_must_bind_route_capture_profile_and_current_artifact(self):
        def mutate(runner, _record, _row):
            runner["route"] = "/wrong"
            runner["captureProfileId"] = "capture-wrong"
            runner["artifacts"]["current"]["sha256"] = "0" * 64

        _rewrite_runner(self.handoff, "visual", mutate)

        self.assertIn(
            "QA_VISUAL_RUNNER_BINDING_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_structural_runner_dom_snapshot_must_bind_page_region_and_component(self):
        def mutate(runner, _record, _row):
            artifact = runner["artifacts"]["domSnapshot"]
            dom_path = self.handoff / artifact["path"]
            dom = _read_json(dom_path)
            dom["nodes"][0]["regionId"] = "region-missing"
            dom["nodes"][0]["componentId"] = "component-missing"
            _write_json(dom_path, dom)
            artifact["sha256"] = _sha256(dom_path)

        _rewrite_runner(self.handoff, "structural", mutate)

        self.assertIn(
            "QA_STRUCTURAL_DOM_BINDING_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_structural_runner_implementation_snapshot_must_match_target_files(self):
        def mutate(runner, _record, _row):
            artifact = runner["artifacts"]["implementationSnapshot"]
            snapshot_path = self.handoff / artifact["path"]
            snapshot = _read_json(snapshot_path)
            snapshot["entries"][0]["sha256"] = "0" * 64
            _write_json(snapshot_path, snapshot)
            artifact["sha256"] = _sha256(snapshot_path)

        _rewrite_runner(self.handoff, "structural", mutate)

        self.assertIn(
            "QA_STRUCTURAL_IMPLEMENTATION_SNAPSHOT_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_interaction_runner_cases_require_nonempty_passing_assertions(self):
        def mutate(runner, _record, _row):
            runner["testCases"][0]["assertions"] = []
            artifact = runner["artifacts"]["interactionResult"]
            result_path = self.handoff / artifact["path"]
            result = _read_json(result_path)
            result["testCases"] = runner["testCases"]
            _write_json(result_path, result)
            artifact["sha256"] = _sha256(result_path)

        _rewrite_runner(self.handoff, "interaction", mutate)

        self.assertIn(
            "QA_INTERACTION_CASE_ASSERTIONS_REQUIRED",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_qa_artifact_hash_mismatch(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        record_path = self.handoff / rows[0]["evidenceRecordPath"]
        record = _read_json(record_path)
        record["artifacts"]["reference"]["sha256"] = "0" * 64
        _write_json(record_path, record)
        rows[0]["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_ARTIFACT_HASH_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_fabricated_overlay_pixels(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        visual = next(row for row in rows if row["evidenceType"] == "visual")
        _write_image(self.handoff / visual["overlayPath"], size=(18, 12), color="red")
        record_path = self.handoff / visual["evidenceRecordPath"]
        record = _read_json(record_path)
        record["artifacts"]["overlay"]["sha256"] = _sha256(
            self.handoff / visual["overlayPath"]
        )
        _write_json(record_path, record)
        visual["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_OVERLAY_PIXEL_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_fabricated_diff_pixels(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        visual = next(row for row in rows if row["evidenceType"] == "visual")
        _write_image(self.handoff / visual["diffPath"], size=(18, 12), color="white")
        record_path = self.handoff / visual["evidenceRecordPath"]
        record = _read_json(record_path)
        record["artifacts"]["diff"]["sha256"] = _sha256(
            self.handoff / visual["diffPath"]
        )
        _write_json(record_path, record)
        visual["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_DIFF_PIXEL_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_mismatched_qa_image_dimensions(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        visual = next(row for row in rows if row["evidenceType"] == "visual")
        _write_image(self.handoff / visual["diffPath"], size=(9, 6), color="black")
        record_path = self.handoff / visual["evidenceRecordPath"]
        record = _read_json(record_path)
        record["artifacts"]["diff"]["sha256"] = _sha256(
            self.handoff / visual["diffPath"]
        )
        _write_json(record_path, record)
        visual["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_IMAGE_DIMENSION_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_recorded_pixel_ratio_that_differs_from_computed(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        visual = next(row for row in rows if row["evidenceType"] == "visual")
        record_path = self.handoff / visual["evidenceRecordPath"]
        record = _read_json(record_path)
        record["checks"][0]["actualPixelRatio"] = 0.5
        _write_json(record_path, record)
        visual["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_PIXEL_RATIO_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_visual_pixel_ratio_above_region_tolerance(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        visual = next(row for row in rows if row["evidenceType"] == "visual")
        current = Image.open(self.handoff / visual["currentPath"]).convert("RGBA")
        current.putpixel((0, 0), (255, 0, 0, 255))
        current.save(self.handoff / visual["currentPath"])
        reference = Image.open(self.handoff / visual["referencePath"]).convert("RGBA")
        Image.blend(reference, current, 0.5).save(self.handoff / visual["overlayPath"])
        ImageChops.difference(reference, current).save(self.handoff / visual["diffPath"])
        record_path = self.handoff / visual["evidenceRecordPath"]
        record = _read_json(record_path)
        record["checks"][0]["actualPixelRatio"] = 1 / (
            reference.width * reference.height
        )
        for name in ("current", "overlay", "diff"):
            record["artifacts"][name]["sha256"] = _sha256(
                self.handoff / visual[f"{name}Path"]
            )
        _write_json(record_path, record)
        visual["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_PIXEL_RATIO_EXCEEDS_TOLERANCE",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_structural_checks_that_do_not_resolve(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        structural = next(row for row in rows if row["evidenceType"] == "structural")
        record_path = self.handoff / structural["evidenceRecordPath"]
        record = _read_json(record_path)
        for check in record["checks"]:
            if check["checkType"] == "requirement-map":
                check["requirementId"] = "R999"
            elif check["checkType"] == "region-map":
                check["regionId"] = "region-missing"
            elif check["checkType"] == "component-map":
                check["componentId"] = "component-missing"
        _write_json(record_path, record)
        structural["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        codes = self.codes(self.validate(source_root=self.source))

        self.assertTrue(
            {
                "QA_STRUCTURAL_REQUIREMENT_NOT_FOUND",
                "QA_STRUCTURAL_REGION_NOT_FOUND",
                "QA_STRUCTURAL_COMPONENT_NOT_FOUND",
            }.issubset(codes),
            codes,
        )

    def test_reports_interaction_check_that_does_not_resolve(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        interaction = next(row for row in rows if row["evidenceType"] == "interaction")
        record_path = self.handoff / interaction["evidenceRecordPath"]
        record = _read_json(record_path)
        record["checks"][0]["interactionId"] = "interaction-missing"
        _write_json(record_path, record)
        interaction["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_INTERACTION_NOT_FOUND",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_malformed_json(self):
        (self.handoff / "contracts" / "page-inventory.json").write_text(
            "{not-json", encoding="utf-8"
        )
        _refresh_design_lock(self.handoff)

        self.assertIn("MALFORMED_JSON", self.codes(self.validate()))

    def test_rejects_nonfinite_numbers_in_machine_contract_json(self):
        path = self.handoff / "contracts" / "diff-regions.json"
        original = path.read_text(encoding="utf-8")
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                path.write_text(
                    original.replace('"pixelRatio": 0', f'"pixelRatio": {constant}'),
                    encoding="utf-8",
                )
                _refresh_design_lock(self.handoff)

                self.assertIn(
                    "MALFORMED_JSON",
                    self.codes(self.validate(source_root=self.source)),
                )

    def test_rejects_nonfinite_visual_metric_in_evidence_record(self):
        qa_path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(qa_path)
        visual = next(row for row in rows if row["evidenceType"] == "visual")
        record_path = self.handoff / visual["evidenceRecordPath"]
        record = _read_json(record_path)
        record["checks"][0]["actualPixelRatio"] = float("nan")
        _write_json(record_path, record)
        visual["evidenceRecordSha256"] = _sha256(record_path)
        _write_csv(qa_path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "QA_EVIDENCE_RECORD_INVALID_JSON",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_malformed_csv(self):
        (self.handoff / "contracts" / "visual-qa-matrix.csv").write_text(
            'qaId,pageId\n"unterminated', encoding="utf-8"
        )
        _refresh_design_lock(self.handoff)

        self.assertIn("MALFORMED_CSV", self.codes(self.validate()))

    def test_reports_source_hash_drift(self):
        _write_image(self.source / "screen.png", color="red")

        self.assertIn(
            "SOURCE_HASH_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_supported_source_image_omitted_from_manifest(self):
        _write_image(self.source / "extra.png", color="orange")

        result = self.validate(source_root=self.source)

        self.assertIn("SOURCE_SET_COVERAGE_MISMATCH", self.codes(result))
        issue = next(
            issue
            for issue in result["issues"]
            if issue["code"] == "SOURCE_SET_COVERAGE_MISMATCH"
        )
        self.assertEqual(issue["missingFromManifest"], ["extra.png"])

    def test_reports_duplicate_manifest_asset_source_and_delivery_identities(self):
        path = self.handoff / "contracts" / "asset-manifest.json"
        manifest = _read_json(path)
        manifest["assets"].append(dict(manifest["assets"][0]))
        _write_json(path, manifest)
        _refresh_design_lock(self.handoff)

        codes = self.codes(self.validate(source_root=self.source))

        self.assertTrue(
            {
                "DUPLICATE_ASSET_ID",
                "DUPLICATE_SOURCE_RELATIVE_PATH",
                "DUPLICATE_DELIVERY_RELATIVE_PATH",
            }.issubset(codes),
            codes,
        )

    def test_reports_delivery_copy_hash_drift(self):
        manifest = _read_json(self.handoff / "contracts" / "asset-manifest.json")
        copy = self.handoff / manifest["assets"][0]["deliveryRelativePath"]
        _write_image(copy, color="green")

        self.assertIn("COPY_HASH_MISMATCH", self.codes(self.validate()))

    def test_reports_duplicate_page_state_variant_identity(self):
        path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(path)
        inventory["pages"].append(dict(inventory["pages"][0]))
        _write_json(path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn("DUPLICATE_TARGET_IDENTITY", self.codes(self.validate()))

    def test_reports_absolute_path_leak(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["currentPath"] = r"C:\captures\current.png"
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("ABSOLUTE_PATH", self.codes(self.validate()))

    def test_reports_absolute_target_file_in_machine_contract(self):
        path = self.handoff / "contracts" / "implementation-map.json"
        implementation_map = _read_json(path)
        implementation_map["mappings"][0]["targetFiles"] = [r"C:\app\page.py"]
        _write_json(path, implementation_map)
        _refresh_design_lock(self.handoff)

        self.assertIn("ABSOLUTE_PATH", self.codes(self.validate()))

    def test_reports_broken_relative_markdown_link(self):
        for locale in ("zh", "en"):
            page = next((self.handoff / "docs" / locale / "pages").glob("*.md"))
            text = page.read_text(encoding="utf-8")
            text = text.replace("../../../assets/", "../../../missing-assets/")
            page.write_text(text, encoding="utf-8")
        _refresh_design_lock(self.handoff)

        self.assertIn("BROKEN_RELATIVE_LINK", self.codes(self.validate()))

    def test_reports_missing_page_document(self):
        next((self.handoff / "docs" / "en" / "pages").glob("*.md")).unlink()
        _refresh_design_lock(self.handoff)

        self.assertIn("MISSING_PAGE_DOCUMENT", self.codes(self.validate()))

    def test_reports_unknown_state_without_gap_id(self):
        path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(path)
        inventory["pages"][0]["route"]["evidenceLevel"] = "unknown"
        inventory["pages"][0]["route"]["gapId"] = None
        _write_json(path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn("UNKNOWN_WITHOUT_GAP_ID", self.codes(self.validate()))

    def test_reports_unknown_state_with_missing_gap_reference(self):
        path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(path)
        inventory["pages"][0]["route"].update(
            {"evidenceLevel": "unknown", "gapId": "G999"}
        )
        _write_json(path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn("GAP_ID_NOT_FOUND", self.codes(self.validate()))

    def test_reports_unknown_state_linked_to_any_resolved_gap_status(self):
        path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(path)
        inventory["pages"][0]["route"].update(
            {"evidenceLevel": "unknown", "gapId": "G001"}
        )
        _write_json(path, inventory)
        gap_path = self.handoff / "contracts" / "gap-register.csv"
        gap_rows = _read_csv(gap_path)

        for status in ("resolved", "closed", "approved", "accepted", "waived"):
            with self.subTest(status=status):
                gap_rows[0]["status"] = status
                _write_csv(gap_path, gap_rows, list(gap_rows[0]))
                _refresh_design_lock(self.handoff)

                self.assertIn(
                    "UNKNOWN_REFERENCES_RESOLVED_GAP", self.codes(self.validate())
                )

    def test_reports_missing_gap_reference_from_requirement_ledger(self):
        path = self.handoff / "contracts" / "requirement-ledger.csv"
        rows = _read_csv(path)
        rows[0].update(
            {"evidenceLevel": "unknown", "status": "proposed", "gapId": "G999"}
        )
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("GAP_ID_NOT_FOUND", self.codes(self.validate()))

    def test_preserves_bilingual_parity_issue_codes(self):
        page = next((self.handoff / "docs" / "en" / "pages").glob("*.md"))
        text = page.read_text(encoding="utf-8")
        page.write_text(
            text.replace("sectionId: identity", "sectionId: changed-identity"),
            encoding="utf-8",
        )
        _refresh_design_lock(self.handoff)

        self.assertIn("BILINGUAL_SECTION_ID_MISMATCH", self.codes(self.validate()))

    def test_reports_incomplete_capture_profile(self):
        path = self.handoff / "contracts" / "capture-profile.json"
        capture = _read_json(path)
        capture["profiles"][0]["browser"] = "unclassified"
        _write_json(path, capture)
        _refresh_design_lock(self.handoff)

        self.assertIn("INCOMPLETE_CAPTURE_PROFILE", self.codes(self.validate()))

    def test_reports_missing_diff_coverage(self):
        path = self.handoff / "contracts" / "diff-regions.json"
        diff = _read_json(path)
        diff["pages"].clear()
        _write_json(path, diff)
        _refresh_design_lock(self.handoff)

        self.assertIn("MISSING_DIFF_COVERAGE", self.codes(self.validate()))

    def test_reports_missing_visual_structural_or_interaction_qa_coverage(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = [row for row in _read_csv(path) if row["evidenceType"] != "interaction"]
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("MISSING_QA_COVERAGE", self.codes(self.validate()))

    def test_reports_open_blocker_and_major_gaps(self):
        path = self.handoff / "contracts" / "gap-register.csv"
        rows = _read_csv(path)
        rows[0]["status"] = "open"
        rows[0]["severity"] = "blocker"
        rows[1]["status"] = "open"
        rows[1]["severity"] = "major"
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        codes = self.codes(self.validate())

        self.assertIn("OPEN_BLOCKER_GAP", codes)
        self.assertIn("OPEN_MAJOR_GAP", codes)

    def test_reports_design_lock_hash_and_contract_material_drift(self):
        readme = self.handoff / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        lock_path = self.handoff / "contracts" / "design-lock.json"
        lock = _read_json(lock_path)
        lock["contractsHash"] = "0" * 64
        _write_json(lock_path, lock)

        codes = self.codes(self.validate())

        self.assertIn("DESIGN_LOCK_FILE_HASH_MISMATCH", codes)
        self.assertIn("DESIGN_LOCK_CONTRACTS_HASH_MISMATCH", codes)

    def test_git_check_is_skipped_without_repository_and_does_not_initialize_one(self):
        repo = self.root / "not-a-repository"
        repo.mkdir()

        result = self.validate(repo_root=repo, allowed_git_prefix="allowed")

        self.assertEqual(result["checks"]["git"]["status"], "skipped")
        self.assertFalse((repo / ".git").exists())

    def test_git_probe_launch_error_is_reported_as_skipped(self):
        validator = _load_module(VALIDATE_PATH, "validate_git_probe_error")

        with mock.patch.object(
            validator.subprocess, "run", side_effect=OSError("git unavailable")
        ):
            result = validator.validate_handoff(
                self.handoff,
                repo_root=self.root,
                allowed_git_prefix="allowed",
            )

        self.assertEqual(result["checks"]["git"]["status"], "skipped")
        self.assertEqual(result["checks"]["git"]["reason"], "git-unavailable")

    def test_git_staged_query_launch_error_returns_stable_failed_report(self):
        validator = _load_module(VALIDATE_PATH, "validate_git_staged_error")
        repository_probe = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="true\n", stderr=""
        )

        with mock.patch.object(
            validator.subprocess,
            "run",
            side_effect=(repository_probe, OSError("git disappeared")),
        ):
            result = validator.validate_handoff(
                self.handoff,
                repo_root=self.root,
                allowed_git_prefix="allowed",
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["checks"]["git"]["status"], "failed")
        self.assertIn("GIT_STATUS_FAILED", self.codes(result))
        self.assertEqual(
            _read_json(self.handoff / "reports" / "validation-report.json"), result
        )

    def test_reports_staged_file_outside_optional_git_allowlist(self):
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        outside = self.root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "outside.txt"], cwd=self.root, check=True, capture_output=True
        )

        result = self.validate(repo_root=self.root, allowed_git_prefix="allowed")

        self.assertIn("GIT_STAGED_PATH_OUTSIDE_ALLOWLIST", self.codes(result))
        self.assertIn("outside.txt", result["checks"]["git"]["stagedPaths"])

    def test_cli_emits_json_and_returns_nonzero_on_errors(self):
        (self.handoff / "README.md").unlink()
        completed = subprocess.run(
            [sys.executable, str(VALIDATE_PATH), "--handoff-root", str(self.handoff)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout)["status"], "failed")


if __name__ == "__main__":
    unittest.main()

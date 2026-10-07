# pylint: disable=C0201
__copyright__ = 'Copyright 2022-2026 Siemens Energy AG'
__author__ = 'Benedikt Kuehne, Eren Erguer'
__license__ = 'MIT'

import builtins
import csv
import json
import logging
import os
import re
import zipfile

from pathlib import Path

from django.conf import settings
from django.db import DatabaseError

from dashboard.models import SoftwareBillOfMaterial, SoftwareInfo, Vulnerability, Result
from uploader.models import FirmwareAnalysis


logger = logging.getLogger(__name__)

EMBARK_EXPORT_FORMAT = "embark-export"
EMBARK_EXPORT_VERSION = 1

CSV_IMPORTERS = {
    "base_aggregator": "f50_csv",
    "vul_aggregator": "f20_csv",
}

def import_results(zip_path, analysis_id, status_callback=None, extract_root=None):
    """
    Import an archive into an EMBArk analysis.

    Two archive formats are supported:

    1. EMBArk export
       Identified through manifest.json.

    2. Native EMBA output
       No manifest required. Relevant files are discovered by searching
       the archive and resolving EMBA module names against the installed
       EMBA module architecture.

    In both cases files are normalized into the provided extraction root.
    By default this is <EMBA_LOG_ROOT>/<analysis_id>/emba_logs/, but import
    batches may override it to keep staging and imported payloads separate.
    """

    def report(phase, percentage, message):
        if status_callback is not None:
            status_callback(phase, percentage, message)

    message = f"Importing {zip_path}"
    print(f"[importer] {message}")
    logger.info(message)
    report("Validating archive", 5, "Opening archive and checking contents")

    with zipfile.ZipFile(zip_path, "r") as archive:

        files = index_zip(archive)
        if not files:
            raise ValueError(f"Archive is empty or contains no readable files: {zip_path}")
        report("Scanning archive", 15, f"Indexed {len(files)} files")

        manifest = read_manifest(archive)

        if manifest is not None:
            logger.info(
                "Detected EMBArk export archive (version %s)",
                manifest.get("version"),
            )
            report("Importing export", 30, "Detected EMBArk export archive")

            validate_manifest(manifest)

            import_embark_export(
                archive,
                files,
                analysis_id,
                status_callback=status_callback,
                extract_root=extract_root,
            )

        else:
            logger.info(
                "No EMBArk manifest found. Treating archive as native EMBA output."
            )
            report("Importing native output", 30, "Detected native EMBA output archive")
            import_emba_output(
                archive,
                files,
                analysis_id,
                status_callback=status_callback,
                extract_root=extract_root,
            )


    result = result_read_in(analysis_id, extract_root=extract_root)
    report("Import complete", 100, "Archive extraction complete")
    return result

# ---------------------------------------------------------------------------
# Manifest Functions
# ---------------------------------------------------------------------------

def read_manifest(archive):
    """
    Read manifest.json if it exists.

    Returns:
        dict: Parsed manifest.
        None: No manifest exists.
    """

    try:
        with archive.open("manifest.json") as manifest_file:
            return json.load(manifest_file)

    except KeyError:
        return None

    except json.JSONDecodeError as error:
        raise ValueError("Invalid manifest.json") from error


def validate_manifest(manifest):
    """
    Validate the EMBArk export manifest.
    """

    archive_format = manifest.get("format")
    version = manifest.get("version")

    if archive_format != EMBARK_EXPORT_FORMAT:
        raise ValueError(
            f"Unsupported archive format: {archive_format}"
        )

    if version != EMBARK_EXPORT_VERSION:
        raise ValueError(
            f"Unsupported EMBArk export version: {version}"
        )


# ---------------------------------------------------------------------------
# Importing EMBArk export format
# ---------------------------------------------------------------------------

def import_embark_export(archive, files, analysis_id, status_callback=None, extract_root=None):
    """
    Import an archive produced by the EMBArk exporter.
    """

    def report(phase, percentage, message):
        if status_callback is not None:
            status_callback(phase, percentage, message)

    classified = classify_files(files)

    extract_root = get_extract_root(analysis_id, extract_root)
    total_files = sum(len(classified[key]) for key in ("csv", "sbom", "logs", "html"))
    processed = 0

    # CSV files
    for archive_path in classified["csv"]:
        target = extract_root / archive_path
        extract_archive_file(
            archive,
            archive_path,
            target,
        )
        processed += 1
        report("Extracting export files", min(80, 35 + int((processed / max(total_files, 1)) * 45)), f"Extracted {processed}/{total_files} files")

    # SBOM
    for archive_path in classified["sbom"]:
        target = extract_root / archive_path
        extract_archive_file(
            archive,
            archive_path,
            target,
        )
        processed += 1
        report("Extracting export files", min(80, 35 + int((processed / max(total_files, 1)) * 45)), f"Extracted {processed}/{total_files} files")

    # Logs
    for archive_path in classified["logs"]:
        target = extract_root / archive_path
        extract_archive_file(
            archive,
            archive_path,
            target,
        )
        processed += 1
        report("Extracting export files", min(80, 35 + int((processed / max(total_files, 1)) * 45)), f"Extracted {processed}/{total_files} files")

    # HTML report
    for archive_path in classified["html"]:
        target = extract_root / archive_path
        extract_archive_file(
            archive,
            archive_path,
            target,
        )
        processed += 1
        report("Extracting export files", min(80, 35 + int((processed / max(total_files, 1)) * 45)), f"Extracted {processed}/{total_files} files")


# ---------------------------------------------------------------------------
# Native EMBA import
# ---------------------------------------------------------------------------

def import_emba_output(archive, files, analysis_id, status_callback=None, extract_root=None):
    """
    Import a native EMBA output archive.
    """

    def report(phase, percentage, message):
        if status_callback is not None:
            status_callback(phase, percentage, message)

    discovered = discover_emba_files(
        archive,
        files,
    )

    extract_root = get_extract_root(analysis_id, extract_root)
    total_files = sum(len(discovered[key]) for key in ("csv", "sbom", "logs", "html"))
    processed = 0

    # CSV files
    for entry in discovered["csv"]:
        archive_path = entry["file"]

        target = (
            extract_root
            / "csv_logs"
            / Path(archive_path).name
        )

        extract_archive_file(
            archive,
            archive_path,
            target,
        )
        processed += 1
        report("Extracting EMBA output", min(80, 35 + int((processed / max(total_files, 1)) * 45)), f"Extracted {processed}/{total_files} files")

    # SBOM
    for archive_path in discovered["sbom"]:
        target = (
            extract_root
            / "SBOM"
            / "EMBA_cyclonedx_sbom.json"
        )

        extract_archive_file(
            archive,
            archive_path,
            target,
        )
        processed += 1
        report("Extracting EMBA output", min(80, 35 + int((processed / max(total_files, 1)) * 45)), f"Extracted {processed}/{total_files} files")

        break

    # Logs
    for archive_path in discovered["logs"]:
        target = (
            extract_root
            / "logger"
            / Path(archive_path).name
        )

        extract_archive_file(
            archive,
            archive_path,
            target,
        )
        processed += 1
        report("Extracting EMBA output", min(80, 35 + int((processed / max(total_files, 1)) * 45)), f"Extracted {processed}/{total_files} files")

    # HTML report
    for archive_path in discovered["html"]:
        parts = Path(archive_path).parts

        try:
            html_index = parts.index("html-report")
        except ValueError:
            continue

        relative_path = Path(*parts[html_index:])

        target = extract_root / relative_path

        extract_archive_file(
            archive,
            archive_path,
            target,
        )
        processed += 1
        report("Extracting EMBA output", min(80, 35 + int((processed / max(total_files, 1)) * 45)), f"Extracted {processed}/{total_files} files")


# ---------------------------------------------------------------------------
# Archive discovery
# ---------------------------------------------------------------------------

def index_zip(archive):
    """
    Return all files contained in an archive.
    """

    return [
        name
        for name in archive.namelist()
        if not name.endswith("/")
    ]


def classify_files(files):
    """
    Classify files belonging to the known EMBArk export structure.
    """

    return {
        "csv": [
            file_path
            for file_path in files
            if file_path.startswith("csv_logs/")
            and file_path.endswith(".csv")
        ],

        "sbom": [
            file_path
            for file_path in files
            if file_path.startswith("SBOM/")
            and file_path.endswith(".json")
        ],

        "logs": [
            file_path
            for file_path in files
            if file_path.startswith("logger/")
            and file_path.endswith(".log")
        ],

        "html": [
            file_path
            for file_path in files
            if "html-report/" in file_path
        ],
    }


def get_extract_root(analysis_id, extract_root=None):
    """
    Return the extraction root for an import.

    The default remains the live analysis output tree, but import batches may
    supply a dedicated root such as logroot/<analysis_id>/imports/<importid>/files.
    """

    if extract_root:
        return Path(extract_root)

    return (
        Path(settings.EMBA_LOG_ROOT)
        / str(analysis_id)
        / "emba_logs"
    )


def extract_archive_file(archive, archive_path, target):
    """
    Safely extract one file from an archive.
    """

    target = Path(target)

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with archive.open(archive_path) as source:
        with open(target, "wb") as destination:
            destination.write(source.read())


# ---------------------------------------------------------------------------
# EMBA module discovery
# ---------------------------------------------------------------------------

def get_emba_modules():
    """
    Discover installed EMBA modules as:
        {
            "name": "base_aggregator",
            "number": "f50",
            "path": ...
        }
    """

    modules = {}

    modules_root = Path(settings.EMBA_ROOT) / "modules"

    if not modules_root.is_dir():
        logger.warning(
            "EMBA modules directory does not exist: %s",
            modules_root,
        )
        return modules

    for path in modules_root.iterdir():

        if path.is_dir():
            shell_files = list(path.glob("*.sh"))

        elif path.is_file() and path.suffix == ".sh":
            shell_files = [path]

        else:
            continue

        for shell_file in shell_files:

            module_number, module_name = parse_module_identity(
                shell_file.name,
                file_type="sh"
            )

            if module_name is None:
                continue

            modules[module_name] = {
                "number": module_number,
                "name": module_name,
                "path": shell_file,
            }

    logger.debug(
        "Discovered %d EMBA modules",
        len(modules),
    )

    return modules

def parse_module_identity(filename, file_type="sh"):
    """
    Parse an EMBA module filename by separating name and number.
    Supports both .sh and .csv files.
    
    Args:
        filename: The filename to parse
        file_type: Either 'sh' or 'csv'
    
    Returns:
        Tuple of (module_number, module_name) or (None, None) if not matched
    """

    name = Path(filename).name
    
    if file_type == "csv":
        pattern = r"^(f\d+)_([A-Za-z0-9_]+)\.csv$"
    else:
        pattern = r"^(f\d+)_([A-Za-z0-9_]+)\.sh$"

    match = re.match(pattern, name)

    if not match:
        return None, None

    return match.group(1), match.group(2)

def resolve_module(module_name, emba_modules):
    """
    Resolve an EMBA module by name.
    """

    return emba_modules.get(module_name)


# ---------------------------------------------------------------------------
# Native EMBA file discovery
# ---------------------------------------------------------------------------

def discover_emba_files(archive, files):
    """
    Search a native EMBA archive for relevant output files.
    Returns:
        {
            "csv": [...],
            "sbom": [...],
            "logs": [...],
            "html": [...]
        }
    """

    emba_modules = get_emba_modules()

    discovered = {
        "csv": [],
        "sbom": [],
        "logs": [],
        "html": [],
    }

    for archive_path in files:

        filename = Path(archive_path).name

        # ---------------------------------------------------------------
        # CSV
        # ---------------------------------------------------------------

        if filename.endswith(".csv"):

            module_number, module_name = parse_module_identity(
                filename,
                file_type="csv"
            )

            if module_name is None:
                continue

            module = resolve_module(
                module_name,
                emba_modules,
            )

            if module is None:
                logger.debug(
                    "Ignoring CSV for unknown EMBA module: %s",
                    filename,
                )
                continue

            if module_number != module["number"]:
                logger.info(
                    "Module number differs for %s: "
                    "archive=%s, installed=%s",
                    module_name,
                    module_number,
                    module["number"],
                )

            discovered["csv"].append({
                "file": archive_path,
                "number": module_number,
                "name": module_name,
            })

            continue

        # ---------------------------------------------------------------
        # SBOM
        # ---------------------------------------------------------------

        if filename == "EMBA_cyclonedx_sbom.json":
            discovered["sbom"].append(archive_path)
            continue

        # ---------------------------------------------------------------
        # HTML report
        # ---------------------------------------------------------------

        if "html-report" in Path(archive_path).parts:
            discovered["html"].append(archive_path)
            continue

        # ---------------------------------------------------------------
        # Logs
        # ---------------------------------------------------------------

        if filename.endswith(".log"):
            discovered["logs"].append(archive_path)

    logger.debug(
        "Discovered native EMBA files: %s",
        discovered,
    )

    return discovered


# ---------------------------------------------------------------------------
# Database read-in
# ---------------------------------------------------------------------------

def result_read_in(analysis_id, extract_root=None):
    """
    Read imported CSVs and SBOM and populate the database.
    """

    logger.debug(
        "Starting read-in of %s",
        analysis_id,
    )

    res = None

    base_root = Path(extract_root) if extract_root else (
        Path(settings.EMBA_LOG_ROOT)
        / str(analysis_id)
        / "emba_logs"
    )

    csv_directory = base_root / "csv_logs"

    if csv_directory.is_dir():

        for file_path in csv_directory.glob("*.csv"):

            module_number, module_name = parse_module_identity(
                file_path.name,
                file_type="csv"
            )

            if module_name is None:
                logger.warning(
                    "Could not identify CSV module: %s",
                    file_path.name,
                )
                continue

            importer_name = CSV_IMPORTERS.get(module_name)

            if importer_name is None:
                logger.info(
                    "Skipping unsupported module %s_%s",
                    module_number,
                    module_name,
                )
                continue

            importer = globals()[importer_name]

            logger.debug(
                "Importing module %s_%s using %s",
                module_number,
                module_name,
                importer_name,
            )

            res = importer(
                str(file_path),
                analysis_id,
            )

    # -------------------------------------------------------------------
    # SBOM
    # -------------------------------------------------------------------

    sbom_file = base_root / "SBOM" / "EMBA_cyclonedx_sbom.json"

    if sbom_file.is_file():

        logger.debug(
            "Importing SBOM"
        )

        try:
            res = sbom_json(
                sbom_file,
                analysis_id,
            )

        except DatabaseError as error:
            logger.error(
                "DB error while importing SBOM: %s",
                error,
                exc_info=True,
            )
            raise

    return res


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def read_csv(path):
    """
    Read an EMBA semicolon-separated CSV.

    Returns a nested dictionary matching the historical EMBArk importer
    structure.
    """

    res_dict = {}

    with open(
        path,
        mode="r",
        encoding="utf-8",
    ) as csv_file:

        csv_reader = csv.reader(
            csv_file,
            delimiter=";",
        )

        for row in csv_reader:

            if not row:
                continue

            # Remove empty / NA values from the end of the row.
            while row and row[-1] in ("", "NA"):
                row.pop()

            if not row:
                continue

            if len(row) == 2:

                if row[0] not in res_dict:
                    res_dict[row[0]] = row[1]

            elif len(row) > 2:

                if row[0] not in res_dict:
                    res_dict[row[0]] = {}

                if len(row[2:]) > 1:

                    if row[1] not in res_dict[row[0]]:
                        res_dict[row[0]][row[1]] = {}

                    res_dict[row[0]][row[1]].update(
                        {
                            row[index]: row[index + 1]
                            for index in range(
                                2,
                                len(row) - 1,
                                2,
                            )
                        }
                    )

                else:
                    res_dict[row[0]][row[1]] = row[2]

    logger.info(
        "result dict: %s",
        res_dict,
    )

    return res_dict

# ---------------------------------------------------------------------------
# Old Functions
# ---------------------------------------------------------------------------

def f50_csv(file_path, analysis_id):
    """
    return: result object/ None
    """
    logger.debug("starting f50 csv import")
    res_dict = read_csv(path=file_path)

    res_dict.pop('FW_path', None)
    entropy_value = res_dict.get("entropy_value", 0)
    # if type(entropy_value) is str:
    if isinstance(entropy_value, str):
        # entropy_value = re.findall(r'(\d+\.?\d*)', ' 7.55 bits per byte.')[0]
        entropy_value = re.findall(r'(\d+\.?\d*)', entropy_value)[0]
    res, _created = Result.objects.get_or_create(
        firmware_analysis=FirmwareAnalysis.objects.get(id=analysis_id)
    )
    if _created:
        try:
            res.emba_command = res_dict.get("emba_command", '')
            res.architecture_verified = res_dict.get("architecture_verified", '')
            # res.os_unverified=res_dict.get("os_unverified", '')
            res.os_verified = res_dict.get("os_verified", '')
            res.files = int(res_dict.get("files", 0))
            res.directories = int(res_dict.get("directories", 0))
            res.entropy_value = float(entropy_value)
            res.shell_scripts = int(res_dict.get("shell_scripts", 0))
            res.shell_script_vulns = int(res_dict.get("shell_script_vulns", 0))
            res.kernel_modules = int(res_dict.get("kernel_modules", 0))
            res.kernel_modules_lic = int(res_dict.get("kernel_modules_lic", 0))
            res.interesting_files = int(res_dict.get("interesting_files", 0))
            res.post_files = int(res_dict.get("post_files", 0))
            res.canary = int(res_dict.get("canary", 0))
            res.canary_per = int(res_dict.get("canary_per", 0))
            res.relro = int(res_dict.get("relro", 0))
            res.relro_per = int(res_dict.get("relro_per", 0))
            res.no_exec = int(res_dict.get("nx", 0))
            res.no_exec_per = int(res_dict.get("nx_per", 0))
            res.pie = int(res_dict.get("pie", 0))
            res.pie_per = int(res_dict.get("pie_per", 0))
            res.stripped = int(res_dict.get("stripped", 0))
            res.stripped_per = int(res_dict.get("stripped_per", 0))
            res.bins_checked = int(res_dict.get("bins_checked", 0))
            res.strcpy = int(res_dict.get("strcpy", 0))
            res.strcpy_bin = json.dumps(res_dict.get("strcpy_bin", {}))
            res.system_bin = json.dumps(res_dict.get("system_bin", {}))
            res.versions_identified = int(res_dict.get("versions_identified", 0))
            # 'cve_high': {'614': '17'}, 'cve_medium': {'1247': '13'}, 'cve_low': {'20': '0'}
            res.cve_critical = json.dumps(res_dict.get("cve_critical", {'0': '0'}).popitem())
            res.cve_high = json.dumps(res_dict.get("cve_high", {'0': '0'}).popitem())
            res.cve_medium = json.dumps(res_dict.get("cve_medium", {'0': '0'}).popitem())
            res.cve_low = json.dumps(res_dict.get("cve_low", {'0': '0'}).popitem())
            res.exploits = int(res_dict.get("exploits", 0))
            res.metasploit_modules = int(res_dict.get("metasploit_modules", 0))
            res.certificates = int(res_dict.get("certificates", 0))
            res.certificates_outdated = int(res_dict.get("certificates_outdated", 0))
        except builtins.Exception as error:
            logger.error("Error in f50_csv: %s", error)
        res.save()
    return res


def f20_csv(file_path, analysis_id=None):
    """
    csv read for f20 (where every line is a CVE)

    return: result object/ None
    """
    logger.debug("starting f20 csv import")
    res_dict = {}
    with open(file_path, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        next(csv_reader)  # skip first line
        for row in csv_reader:
            try:
                res_dict[row[2]] = {
                    'Binary': row[0],
                    'Version': row[1],
                    'CVSS': row[3],
                    'exploit db exploit available': row[4],
                    'metasploit module': row[5],
                    'trickest PoC': row[6],
                    'Routersploit': row[7],
                    'local exploit': row[8],
                    'remote exploit': row[9],
                    'DoS exploit': row[10],
                    'known exploited vuln': row[11]
                }
            except builtins.Exception as error_:
                logger.error("Error in f20 readin: %s", error_)
                logger.error("row got %i memebers", len(row))
        logger.debug("Got the following res_dict: %s", res_dict)
    res, _ = Result.objects.get_or_create(
        firmware_analysis=FirmwareAnalysis.objects.get(id=analysis_id)
    )
    for key_, value_ in res_dict.items():
        try:
            new_vulnerability, add_ = Vulnerability.objects.update_or_create(
                cve=key_,
                info=value_
            )
            logger.debug("Adding Vuln: %s to res %s", new_vulnerability, res)
            if add_:
                res.vulnerability.add(new_vulnerability)
        except builtins.Exception as error_:
            logger.error("Error in f20 readin: %s", error_)
            logger.error("Key is %s ; Was new? %s; Info is %s", key_, add_, value_)
    logger.debug("read f20 csv done")
    return res


def f10_csv(_file_path, _analysis_id):
    """
    return: result object/ None
    """
    logger.debug("starting f10 csv import")
    # FIXME needs implementation
    logger.debug("read f10 csv done")


def sbom_json(_file_path, _analysis_id):
    """
    return: result obj/ None
    SBOM json
    """
    logger.debug("starting SBOM json import")
    json_data = read_cyclone_dx_json(_file_path)
    serial = json_data.get('serialNumber')
    logger.debug("Reading SBOM serial=%s", serial)

    # Always create a fresh SBOM record for each import so a Result can
    # reference a unique SBOM (avoids OneToOne conflicts when the same
    # serial is imported multiple times).
    sbom_obj = SoftwareBillOfMaterial.objects.create(
        meta=serial or "NA",
        file=_file_path,
    )
    logger.debug("Created SBOM record %s for serial %s", sbom_obj.id, serial)

    # populate components if present
    components = json_data.get('components', [])
    if components:
        logger.debug("Trying to read %s components", len(components))
        for component_ in components:
            try:
                # Reuse existing SoftwareInfo entries when the component
                # has a stable `bom-ref`; otherwise create a new one.
                comp_id = component_.get('bom-ref')
                if comp_id:
                    new_sitem, add_sitem = SoftwareInfo.objects.get_or_create(
                        id=comp_id,
                        defaults={
                            'name': component_.get('name', 'NA'),
                            'type': component_.get('type', 'NA'),
                            'supplier': component_.get('supplier') or 'NA',
                            'license': json.dumps(component_.get('licenses')) or 'NA',
                            'group': component_.get('group') or 'NA',
                            'version': component_.get('version') or 'NA',
                            'hashes': [f"{json.dumps(entry)}" for entry in component_.get('hashes', [])],
                            'cpe': component_.get('cpe') or 'NA',
                            'purl': component_.get('purl') or 'NA',
                            'properties': component_.get('properties') or 'NA',
                        }
                    )
                else:
                    new_sitem = SoftwareInfo.objects.create(
                        name=component_.get('name', 'NA'),
                        type=component_.get('type', 'NA'),
                        supplier=component_.get('supplier') or 'NA',
                        license=json.dumps(component_.get('licenses')) or 'NA',
                        group=component_.get('group') or 'NA',
                        version=component_.get('version') or 'NA',
                        hashes=[f"{json.dumps(entry)}" for entry in component_.get('hashes', [])],
                        cpe=component_.get('cpe') or 'NA',
                        purl=component_.get('purl') or 'NA',
                        properties=component_.get('properties') or 'NA',
                    )

                logger.debug("Adding SBOM item: %s to sbom %s", new_sitem, sbom_obj)
                sbom_obj.component.add(new_sitem)
            except builtins.Exception as error_:
                logger.exception("Failed to import SBOM component: %s", component_)
    sbom_obj.save()
    res, _ = Result.objects.get_or_create(
        firmware_analysis=FirmwareAnalysis.objects.get(id=_analysis_id),
    )
    res.sbom = sbom_obj
    res.save()
    logger.debug("read f15 json done")
    return res


def read_cyclone_dx_json(_file_path):
    """
    returns json
    """
    with open(_file_path, 'r', encoding='utf-8') as json_file:
        # TODO validate the sbom
        return json.load(json_file)
        

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    TEST_DIR = os.path.join(BASE_DIR, 'test/porter')
    #test print f50
    #with open(os.path.join(TEST_DIR, 'f50_test.json'), 'w', encoding='utf-8') as json_file:
    #    json_file.write(json.dumps(read_csv(os.path.join(TEST_DIR, 'f50_test.csv')), indent=4))
    #
    # with open(os.path.join(TEST_DIR, 'f50_test.json'), 'w', encoding='utf-8') as output_file:
    #     json_data = read_cyclone_dx_json(os.path.join(TEST_DIR, 'EMBA_cyclonedx_sbom.json'))
    #     for component_ in json_data['components']
    #         output_file.write(json.dumps(component_, indent=4))
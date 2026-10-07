__copyright__ = 'Copyright 2022-2026 Siemens Energy AG'
__author__ = 'Benedikt Kuehne, Eren Erguer'
__license__ = 'MIT'

from pathlib import Path
import json
import logging
import zipfile

from django.conf import settings
from uploader.models import FirmwareAnalysis

logger = logging.getLogger(__name__)


def export_results(analysis_id, export_options, export_id):
    """
    Create an EMBArk export ZIP containing the selected
    analysis components.
    :param: analysis_id
    :param: export_options
    :return: zip_path

    Template:
        export.zip
        ├── csv_logs/
        │   ├── f50_base_aggregator.csv     
        │   └── f14_tag_builder.csv
        ├── SBOM/
        │   └── EMBA_cyclonedx_sbom.json
        ├── logger/
        │   ├── emba.log
        │   └── emba_error.log
        └── html-report/
            ├── index.html
            ├── emba.html
            ├── style/
            ├── f50_base_aggregator/
            ├── f17_cve_bin_tool.html
            ├── s05_firmware_details.html
            └── ...
    """

    base_dir = Path(settings.EMBA_LOG_ROOT) / str(analysis_id)

    emba_logs_dir = base_dir / "emba_logs"
    export_dir = base_dir / "exports"
    
    export_dir.mkdir(parents=True,exist_ok=True)

    zip_path = export_dir / f"export_{export_id}.zip"

    files_to_export = []

    # MUST HAVE FILES FOR EXPORT
    # TODO: add stronger error/warning for missing files
    # TODO: determine required files and fix module number/name problem
    files_to_export.extend([
        emba_logs_dir / "csv_logs" / "f50_base_aggregator.csv",
        emba_logs_dir / "csv_logs" / "f14_tag_builder.csv",
        emba_logs_dir / "SBOM" / "EMBA_cyclonedx_sbom.json",
    ])

    # CONDITIONAL FILES FOR EXPORT
    if "logs" in export_options:
        files_to_export.extend([
            emba_logs_dir / "emba.log",
            emba_logs_dir / "emba_error.log",
        ])

    analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as zipf:

        zipf.writestr(
            "manifest.json",
            json.dumps(
                {
                    "Username": str(analysis.user),
                    "format": "embark-export",
                    "version": 1,
                    "analysis_id": str(analysis_id),
                    "export_options": export_options,
                },
                indent=4,
            ),
        )

        for file_path in files_to_export:

            if file_path.is_file():

                if file_path.name.endswith(".log"):   

                    zipf.write(
                        file_path,
                        Path("logger") / file_path.name,
                    )

                else:

                    zipf.write(
                        file_path,
                        file_path.relative_to(emba_logs_dir),
                    )
            
            else:

                logger.warning(
                    "Export file missing: %s",
                    file_path,
                )
                
        # HTML HANDLING
        if "html-report" in export_options:

            html_report_dir = emba_logs_dir / "html-report"

            if html_report_dir.is_dir():

                for file_path in html_report_dir.rglob("*"):

                    if file_path.is_file():

                        zipf.write(
                            file_path,
                            file_path.relative_to(emba_logs_dir),
                        )

            else:
                logger.warning(
                    "Export directory missing: %s",
                    html_report_dir,
                )
    return zip_path
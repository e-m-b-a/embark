from pathlib import Path
import json
import logging
import zipfile

from django.conf import settings

logger = logging.getLogger(__name__)


def export_results(analysis_id, zip_path):
    """
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

    base_dir = (
        Path(settings.EMBA_LOG_ROOT)
        / str(analysis_id)
    )

    emba_logs_dir = base_dir / "emba_logs"

    files_to_export = [
        base_dir / "emba_logs" / "csv_logs" / "f50_base_aggregator.csv",    # TODO: update necessary files. add file_search for name/numberID instead of hardcoded file names.
        base_dir / "emba_logs" / "csv_logs" / "f14_tag_builder.csv",
        base_dir / "emba_logs" / "SBOM" / "EMBA_cyclonedx_sbom.json",
        base_dir / "emba_logs" / "emba.log",
        base_dir / "emba_logs" / "emba_error.log"
    ]

    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as zipf:

        zipf.writestr(
            "manifest.json",
            json.dumps(
                {
                    "format": "embark-export",
                    "version": 1,
                    "analysis_id": str(analysis_id),
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
                
            html_report_dir = emba_logs_dir / "html-report"     # TODO: remove html-report hardcode for directories_to_export for easier inputting

            if html_report_dir.is_dir():
                for file_path in html_report_dir.rglob("*"):
                    if file_path.is_file():
                        zipf.write(
                            file_path,
                            file_path.relative_to(emba_logs_dir),
                        )
            else:
                logger.warning("Export directory missing: %s", html_report_dir)
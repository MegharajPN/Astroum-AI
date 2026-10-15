from django.conf import settings
from django.core.management.base import BaseCommand

from brahmo.ingest import load_all


class Command(BaseCommand):
    help = "Load the assessment data packet into MySQL. Idempotent per file hash; provenance per batch."

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", default=str(settings.DATA_DIR),
                            help="Folder holding the packet files (default: <repo>/data).")
        parser.add_argument("--replace", action="store_true",
                            help="Clear and reload each dataset even if its file hash already loaded.")

    def handle(self, *args, **options):
        for result in load_all(options["data_dir"], replace=options["replace"]):
            self.stdout.write(str(result))
        self.stdout.write(self.style.SUCCESS("Done. Review open gaps at /api/gaps/?status=OPEN"))

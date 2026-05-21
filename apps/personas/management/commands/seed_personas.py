from django.core.management.base import BaseCommand
from apps.personas.services.get_persona import seed_builtin_personas


class Command(BaseCommand):
    help = "Seed the database with built-in Oracle Brain personas"

    def handle(self, *args, **kwargs):
        seed_builtin_personas()
        self.stdout.write(self.style.SUCCESS("Built-in personas seeded successfully."))

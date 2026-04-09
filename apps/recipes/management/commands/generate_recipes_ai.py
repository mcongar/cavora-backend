"""
Generate and publish recipes via OpenAI (batch seeding).

Examples:
  python manage.py generate_recipes_ai --count 3 --theme "desayunos saludables"
  python manage.py generate_recipes_ai --count 1 --theme "pasta" --slugs tomato,garlic
Requires OPENAI_API_KEY and RECIPE_AI_ENABLED=true.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.recipes.services.ai_recipe_generator import AiRecipeGenerationError, OpenAINotConfiguredError
from apps.recipes.services.ai_recipe_service import generate_batch_recipe


class Command(BaseCommand):
    help = "Create N published AI recipes (optional anchor slugs must exist in DB)."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=1)
        parser.add_argument(
            "--theme",
            type=str,
            default="",
            help="Short theme for the model (e.g. 'comfort food', 'meal prep').",
        )
        parser.add_argument(
            "--slugs",
            type=str,
            default="",
            help="Comma-separated existing ingredient slugs to anchor every recipe.",
        )
        parser.add_argument(
            "--language",
            type=str,
            default="es",
            choices=["es", "en"],
        )

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1 or count > 50:
            raise CommandError("--count must be between 1 and 50.")
        theme = (options["theme"] or "").strip()
        slugs_raw = options["slugs"] or ""
        anchor_slugs = [s.strip().lower() for s in slugs_raw.split(",") if s.strip()]
        if not theme:
            raise CommandError("Provide a non-empty --theme (e.g. --theme 'recetas de invierno').")

        lang = options["language"]
        created = []
        for i in range(count):
            try:
                r = generate_batch_recipe(theme=theme, anchor_slugs=anchor_slugs or None, language=lang)
            except OpenAINotConfiguredError as e:
                raise CommandError(str(e)) from e
            except AiRecipeGenerationError as e:
                raise CommandError(str(e)) from e
            except ValueError as e:
                raise CommandError(str(e)) from e
            created.append(str(r.id))
            self.stdout.write(self.style.SUCCESS(f"[{i + 1}/{count}] {r.title_es} ({r.id})"))

        self.stdout.write(self.style.NOTICE(f"Done. {len(created)} recipe(s) created."))

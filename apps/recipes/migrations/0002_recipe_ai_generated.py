from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recipes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="recipe",
            name="ai_generated",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Created by the AI recipe generator (batch or on-demand).",
            ),
        ),
    ]

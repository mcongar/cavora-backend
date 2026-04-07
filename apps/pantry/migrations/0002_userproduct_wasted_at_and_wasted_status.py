# Generated manually for WASTED status and wasted_at timestamp

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pantry", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userproduct",
            name="wasted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="userproduct",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("consumed", "Consumed"),
                    ("expired", "Expired"),
                    ("removed", "Removed"),
                    ("wasted", "Wasted"),
                ],
                default="active",
                max_length=20,
            ),
        ),
    ]

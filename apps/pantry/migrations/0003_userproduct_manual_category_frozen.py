from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pantry", "0002_userproduct_wasted_at_and_wasted_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="userproduct",
            name="manual_category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("dairy", "Dairy"),
                    ("fruits", "Fruits"),
                    ("vegetables", "Vegetables"),
                    ("meat", "Meat"),
                    ("fish", "Fish"),
                    ("beverages", "Beverages"),
                    ("snacks", "Snacks"),
                    ("cereals", "Cereals"),
                    ("frozen", "Frozen"),
                    ("condiments", "Condiments"),
                    ("bakery", "Bakery"),
                    ("canned", "Canned"),
                    ("other", "Other"),
                ],
                help_text="When catalog_product is null: user-chosen category for hints and display.",
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="userproduct",
            name="is_frozen",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userproduct",
            name="frozen_at",
            field=models.DateField(blank=True, null=True),
        ),
    ]

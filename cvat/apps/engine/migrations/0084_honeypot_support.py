# Generated by Django 4.2.15 on 2024-09-23 13:11

from typing import Collection

import django.db.models.deletion
from django.db import migrations, models

import cvat.apps.engine.models


def get_frame_step(db_data) -> int:
    v = db_data.frame_filter or "step=1"
    return int(v.split("=")[-1])


def get_rel_frame(abs_frame: int, db_data) -> int:
    data_start_frame = db_data.start_frame
    step = get_frame_step(db_data)
    return (abs_frame - data_start_frame) // step


def get_segment_rel_frame_set(db_segment) -> Collection[int]:
    db_data = db_segment.task.data
    data_start_frame = db_data.start_frame
    data_stop_frame = db_data.stop_frame
    step = get_frame_step(db_data)
    frame_range = range(
        data_start_frame + db_segment.start_frame * step,
        min(data_start_frame + db_segment.stop_frame * step, data_stop_frame) + step,
        step,
    )

    if db_segment.type == "range":
        frame_set = frame_range
    elif db_segment.type == "specific_frames":
        frame_set = set(frame_range).intersection(db_segment.frames or [])
    else:
        raise ValueError(f"Unknown segment type: {db_segment.type}")

    return sorted(get_rel_frame(abs_frame, db_data) for abs_frame in frame_set)


def init_validation_layout_in_tasks_with_gt_job(apps, schema_editor):
    Job = apps.get_model("engine", "Job")
    ValidationLayout = apps.get_model("engine", "ValidationLayout")

    gt_jobs = (
        Job.objects.filter(type="ground_truth")
        .select_related("segment", "segment__task", "segment__task__data")
        .iterator(chunk_size=100)
    )

    validation_layouts = []
    for gt_job in gt_jobs:
        validation_layout = ValidationLayout(
            task_data=gt_job.segment.task.data,
            mode="gt",
            frames=get_segment_rel_frame_set(gt_job.segment),
        )
        validation_layouts.append(validation_layout)

    ValidationLayout.objects.bulk_create(validation_layouts, batch_size=100)


def init_m2m_for_related_files(apps, schema_editor):
    RelatedFile = apps.get_model("engine", "RelatedFile")

    ThroughModel = RelatedFile.images.through
    ThroughModel.objects.bulk_create(
        (
            ThroughModel(relatedfile_id=related_file_id, image_id=image_id)
            for related_file_id, image_id in (
                RelatedFile.objects.filter(primary_image__isnull=False)
                .values_list("id", "primary_image_id")
                .iterator(chunk_size=1000)
            )
        ),
        batch_size=1000,
    )


def revert_m2m_for_related_files(apps, schema_editor):
    RelatedFile = apps.get_model("engine", "RelatedFile")

    if top_related_file_uses := (
        RelatedFile.objects
        .annotate(images_count=models.aggregates.Count(
            "images",
            filter=models.Q(images__is_placeholder=False)
        ))
        .order_by("-images_count")
        .filter(images_count__gt=1)
        .values_list("id", "images_count")[:10]
    ):
        raise Exception(
            "Can't run backward migration: "
            "there are RelatedFile objects with more than 1 related Image. "
            "Top RelatedFile uses: {}".format(
                ", ".join(f"\n\tid = {id}: {count}" for id, count in top_related_file_uses)
            )
        )

    ThroughModel = RelatedFile.images.through

    (
        RelatedFile.objects
        .annotate(images_count=models.aggregates.Count(
            "images",
            filter=models.Q(images__is_placeholder=False)
        ))
        .filter(images_count__gt=0)
        .update(
            primary_image_id=models.Subquery(
                ThroughModel.objects
                .filter(relatedfile_id=models.OuterRef("id"))
                .values_list("image_id", flat=True)[:1]
            )
        )
    )

class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0083_move_to_segment_chunks"),
    ]

    operations = [
        migrations.AddField(
            model_name="image",
            name="is_placeholder",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="image",
            name="real_frame",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="ValidationParams",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "mode",
                    models.CharField(choices=[("gt", "GT"), ("gt_pool", "GT_POOL")], max_length=32),
                ),
                (
                    "frame_selection_method",
                    models.CharField(
                        choices=[
                            ("random_uniform", "RANDOM_UNIFORM"),
                            ("random_per_job", "RANDOM_PER_JOB"),
                            ("manual", "MANUAL"),
                        ],
                        max_length=32,
                    ),
                ),
                ("random_seed", models.IntegerField(null=True)),
                ("frame_count", models.IntegerField(null=True)),
                ("frame_share", models.FloatField(null=True)),
                ("frames_per_job_count", models.IntegerField(null=True)),
                ("frames_per_job_share", models.FloatField(null=True)),
                (
                    "task_data",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="validation_params",
                        to="engine.data",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ValidationLayout",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "mode",
                    models.CharField(choices=[("gt", "GT"), ("gt_pool", "GT_POOL")], max_length=32),
                ),
                ("frames_per_job_count", models.IntegerField(null=True)),
                ("frames", cvat.apps.engine.models.IntArrayField(default="")),
                ("disabled_frames", cvat.apps.engine.models.IntArrayField(default="")),
                (
                    "task_data",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="validation_layout",
                        to="engine.data",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ValidationFrame",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("path", models.CharField(default="", max_length=1024)),
                (
                    "validation_params",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="frames",
                        to="engine.validationparams",
                    ),
                ),
            ],
        ),
        migrations.RunPython(
            init_validation_layout_in_tasks_with_gt_job,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddField(
            model_name="relatedfile",
            name="images",
            field=models.ManyToManyField(to="engine.image"),
        ),
        migrations.RunPython(
            init_m2m_for_related_files,
            reverse_code=revert_m2m_for_related_files,
        ),
        migrations.RemoveField(
            model_name="relatedfile",
            name="primary_image",
            field=models.ForeignKey(
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="related_files",
                to="engine.image",
            ),
        ),
        migrations.AlterField(
            model_name="relatedfile",
            name="images",
            field=models.ManyToManyField(to="engine.image", related_name="related_files"),
        ),
    ]
from backend.app.models import (
    DataEngineeringTask,
    DataEngineeringTaskStep,
    MissingValuesValidationResult,
    DuplicateRowsValidationResult,
)

import pandas as pd

from backend.app.transformation_validation_service import (
    validate_transformation_for_finding,
)

# get_current_task_step()
#
# Bir task içinde junior'ın şu anda
# üzerinde çalışması gereken step'i bulur.
#
# current_step_number:
# Task'ın hangi step'te olduğunu söyler.
#
# Örnek:
#
# current_step_number = 2
#
# steps:
# Step 1
# Step 2
# Step 3
#
# ↓
#
# Step 2 döner.
def get_current_task_step(
    task: DataEngineeringTask,
) -> DataEngineeringTaskStep | None:

    # Task tamamen bittiyse artık aktif step yoktur.
    if task.status == "completed":
        return None

    # Task'ın current_step_number değeri ile
    # aynı step_number'a sahip step'i arıyoruz.
    for step in task.steps:

        if step.step_number == task.current_step_number:
            return step

    # Böyle bir step bulunamazsa None döner.
    return None

def complete_current_task_step(
    task: DataEngineeringTask,
) -> DataEngineeringTask:

    # Task zaten tamamen bittiyse tekrar ilerleyemeyiz.
    if task.status == "completed":
        raise ValueError("Task zaten tamamlanmış.")

    # Junior'ın şu anda üzerinde çalıştığı step'i bul.
    current_step = get_current_task_step(task)

    if current_step is None:
        raise ValueError("Current task step bulunamadı.")

    # Mevcut step artık tamamlandı.
    current_step.status = "completed"

    # Mevcut step'ten sonraki step'i buluyoruz.
    next_step = None

    for step in task.steps:
        if step.step_number > current_step.step_number:

            if (
                next_step is None
                or step.step_number < next_step.step_number
            ):
                next_step = step

    # Sonraki step yoksa bütün task tamamlandı.
    if next_step is None:
        task.status = "completed"
        return task

    # Sonraki step artık junior'ın aktif problemi.
    next_step.status = "active"

    task.current_step_number = next_step.step_number
    task.status = "active"

    return task

# apply_validation_result_to_task()
#
# Junior'ın yaptığı transformation'ın validation sonucuna göre
# task'ın ilerleyip ilerlemeyeceğine karar verir.
#
# success = False
# ↓
# junior aynı step'te kalır
#
# success = True
# ↓
# mevcut step tamamlanır
# ↓
# sonraki step aktif olur
def apply_validation_result_to_task(
    task: DataEngineeringTask,
    validation: (
        MissingValuesValidationResult
        | DuplicateRowsValidationResult
    ),
) -> DataEngineeringTask:

    # Transformation başarılı değilse
    # task üzerinde hiçbir ilerleme yapmıyoruz.
    if not validation.success:
        return task

    # Transformation başarılıysa mevcut step tamamlanabilir.
    return complete_current_task_step(task)


# review_current_task_transformation()
#
# Junior'ın mevcut task step'i için yaptığı
# gerçek transformation'ı değerlendirir.
#
# Akış:
#
# task
# ↓
# current step bulunur
# ↓
# step içindeki finding alınır
# ↓
# before/after DataFrame validate edilir
# ↓
# validation başarılıysa task ilerler
# ↓
# başarısızsa aynı step'te kalır
def review_current_task_transformation(
    task: DataEngineeringTask,
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
) -> DataEngineeringTask:

    current_step = get_current_task_step(task)

    if current_step is None:
        raise ValueError("Current task step bulunamadı.")

    validation = validate_transformation_for_finding(
        before_df=before_df,
        after_df=after_df,
        finding=current_step.finding,
    )

    if validation is None:
        raise ValueError(
            "Bu task step için transformation validation desteklenmiyor."
        )

    return apply_validation_result_to_task(
        task=task,
        validation=validation,
    )
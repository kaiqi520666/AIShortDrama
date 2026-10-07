import { reactive } from 'vue'
import { resolveAdminTaskReview } from '../api/admin'
import { i18n } from '../i18n'
import { useAdminMutation } from './useAdminMutation'

export function useAdminTaskReview({ onResolved } = {}) {
  const { confirmMutation } = useAdminMutation()
  const review = reactive({ task: null, action: 'resume', reason: '', providerTaskId: '', submitting: false })

  function openReview(task) {
    if (review.submitting || task.status !== 'needs_review') return
    Object.assign(review, {
      task,
      action: ['image', 'video', 'audio'].includes(task.task_type) ? 'resume' : 'cancel',
      reason: '',
      providerTaskId: task.provider_task_id || '',
    })
  }

  function closeReview() {
    if (!review.submitting) review.task = null
  }

  async function submitReview() {
    if (review.submitting || !review.task || !review.reason.trim()) return false
    const mutation = {
      taskId: review.task.id,
      taskType: review.task.task_type,
      action: review.action,
      reason: review.reason.trim(),
      providerTaskId: review.providerTaskId.trim(),
    }
    review.submitting = true
    try {
      const { t } = i18n.global
      if (!await confirmMutation({
        title: t(`admin.tasks.reviewActions.${mutation.action}`),
        message: `${mutation.taskId}\n${t(`admin.tasks.reviewNotes.${mutation.action}`)}`,
      })) return false
      const payload = { action: mutation.action, reason: mutation.reason }
      if (mutation.action === 'resume' && ['image', 'video'].includes(mutation.taskType) && mutation.providerTaskId) {
        payload.provider_task_id = mutation.providerTaskId
      }
      const result = await resolveAdminTaskReview(mutation.taskId, payload)
      if (result.code !== 0) throw new Error(result.message)
      review.task = null
      await onResolved?.(result.data)
      return true
    } finally {
      review.submitting = false
    }
  }

  return { review, openReview, closeReview, submitReview }
}

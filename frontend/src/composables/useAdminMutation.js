import { useGlobalConfirm } from './useGlobalUI'

export function useAdminMutation() {
  const { confirm } = useGlobalConfirm()

  function confirmMutation({ title, message }) {
    return confirm({
      title: `确认${title}`,
      message: `${message}\n此操作会立即生效并写入操作审计。`,
      confirmText: '确认提交',
      tone: 'danger',
    })
  }

  return { confirmMutation }
}

import { useGlobalConfirm } from './useGlobalUI'
import { i18n } from '../i18n'

export function useAdminMutation() {
  const { confirm } = useGlobalConfirm()

  function confirmMutation({ title, message }) {
    return confirm({
      title: i18n.global.t('admin.confirmTitle', { title }),
      message: i18n.global.t('admin.confirmMessage', { message }),
      confirmText: i18n.global.t('admin.confirmSubmit'),
      tone: 'danger',
    })
  }

  return { confirmMutation }
}

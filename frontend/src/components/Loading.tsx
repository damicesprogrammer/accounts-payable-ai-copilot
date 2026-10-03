import { useI18n } from '../i18n'

export default function Loading({ text }: { text?: string }) {
  const { t } = useI18n()
  return (
    <div className="flex items-center gap-2 py-6 text-sm text-slate-500" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
      {text ?? t('common.loading')}
    </div>
  )
}

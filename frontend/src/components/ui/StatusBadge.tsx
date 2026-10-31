interface Props { status: string; className?: string }

const MAP: Record<string, string> = {
  active:          'badge-active',
  paused:          'badge-paused',
  closed:          'badge-closed',
  expired:         'badge-overdue',
  draft:           'badge-draft',
  confirmed:       'badge-confirmed',
  quotation:       'badge-draft',
  paid:            'badge-paid',
  partially_paid:  'badge-paused',
  overdue:         'badge-overdue',
  cancelled:       'badge-cancelled',
  sent:            'badge-draft',
}

export default function StatusBadge({ status, className = '' }: Props) {
  const cls = MAP[status] ?? 'badge bg-gray-100 text-gray-600'
  return (
    <span className={`${cls} ${className}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

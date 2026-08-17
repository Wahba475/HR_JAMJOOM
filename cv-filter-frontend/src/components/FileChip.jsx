const FileChip = ({ file, onRemove }) => {
  return (
    <div className="flex items-center bg-surface-2 border border-hairline rounded-full py-xxs px-sm gap-xs">
      <span className="material-symbols-outlined text-ink-subtle text-sm">description</span>
      <span className="text-caption text-ink max-w-37.5 truncate">{file.name}</span>
      <button
        type="button"
        onClick={onRemove}
        className="text-ink-tertiary hover:text-error transition-colors flex items-center ml-xs"
        aria-label={`Remove ${file.name}`}
      >
        <span className="material-symbols-outlined text-sm">close</span>
      </button>
    </div>
  )
}

export default FileChip

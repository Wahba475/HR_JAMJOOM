import { useRef, useState } from 'react'
import toast from 'react-hot-toast'
import FileChip from './FileChip'

const UploadDropzone = ({ files, onFilesChange }) => {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef(null)

  const addFiles = (fileList) => {
    const incoming = Array.from(fileList)
    const pdfs = incoming.filter((f) => f.type === 'application/pdf')

    if (pdfs.length < incoming.length) {
      toast.error('Only PDF files are accepted')
    }

    onFilesChange([...files, ...pdfs])
  }

  const removeFile = (index) => {
    onFilesChange(files.filter((_, i) => i !== index))
  }

  return (
    <div className="flex flex-col gap-sm">
      <label className="text-eyebrow text-ink-subtle uppercase tracking-wider">Upload Resumes</label>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setIsDragging(false)
          addFiles(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        className={`dashed-border rounded-xl transition-colors cursor-pointer flex flex-col items-center justify-center py-md px-md group ${
          isDragging ? 'bg-surface-2' : 'bg-surface-1 hover:bg-surface-2'
        }`}
      >
        <input
          ref={inputRef}
          accept=".pdf"
          className="hidden"
          multiple
          type="file"
          onChange={(e) => {
            addFiles(e.target.files)
            e.target.value = ''
          }}
        />
        <span
          className="material-symbols-outlined text-outline group-hover:text-primary-focus transition-colors text-4xl mb-sm"
          style={{ fontVariationSettings: "'FILL' 0, 'wght' 200" }}
        >
          upload_file
        </span>
        <p className="text-body-lg text-ink font-medium">Drag and drop CVs here...</p>
        <p className="text-body-sm text-ink-subtle mt-xxs">PDF only</p>
      </div>

      {files.length > 0 && (
        <div className="flex flex-wrap gap-xs mt-xs">
          {files.map((file, i) => (
            <FileChip key={`${file.name}-${i}`} file={file} onRemove={() => removeFile(i)} />
          ))}
        </div>
      )}
    </div>
  )
}

export default UploadDropzone

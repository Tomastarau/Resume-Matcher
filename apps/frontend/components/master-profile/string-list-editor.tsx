'use client';

import { useEffect, useState } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

interface StringListEditorProps {
  id: string;
  label: string;
  values: string[];
  placeholder: string;
  onChange: (values: string[]) => void;
}

export function StringListEditor({
  id,
  label,
  values,
  placeholder,
  onChange,
}: StringListEditorProps) {
  const [draftValue, setDraftValue] = useState(values.join('\n'));

  useEffect(() => {
    setDraftValue(values.join('\n'));
  }, [values]);

  const normalizeLines = (value: string): string[] =>
    value
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);

  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="font-mono text-xs uppercase tracking-wider text-gray-600">
        {label}
      </Label>
      <Textarea
        id={id}
        value={draftValue}
        onChange={(event) => {
          setDraftValue(event.target.value);
        }}
        onBlur={() => {
          const normalizedValue = normalizeLines(draftValue).join('\n');
          setDraftValue(normalizedValue);
          onChange(normalizeLines(draftValue));
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            event.stopPropagation();
          }
        }}
        placeholder={placeholder}
        className="min-h-[120px] border-2 border-black bg-white font-sans"
      />
    </div>
  );
}

'use client';

import { Button } from '@/components/ui/button';
import { useTranslations } from '@/lib/i18n';
import FileUp from 'lucide-react/dist/esm/icons/file-up';
import Plus from 'lucide-react/dist/esm/icons/plus';

interface EmptyStateProps {
  canImport: boolean;
  isImporting: boolean;
  onImport: () => void;
  onStart: () => void;
}

export function MasterProfileEmptyState({
  canImport,
  isImporting,
  onImport,
  onStart,
}: EmptyStateProps) {
  const { t } = useTranslations();

  return (
    <div className="border-2 border-black bg-white p-8 shadow-[4px_4px_0px_0px_#000000]">
      <div className="max-w-2xl space-y-4">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-blue-700">
          {t('masterProfile.label')}
        </p>
        <h1 className="font-serif text-4xl font-bold uppercase leading-none">
          {t('masterProfile.emptyState.title')}
        </h1>
        <p className="font-sans text-sm text-gray-700">
          {t('masterProfile.emptyState.description')}
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <Button variant="default" onClick={onStart}>
            <Plus className="w-4 h-4" />
            {t('masterProfile.emptyState.startFromScratch')}
          </Button>
          <Button
            variant="outline"
            onClick={onImport}
            disabled={!canImport || isImporting}
            title={
              canImport
                ? t('masterProfile.emptyState.importTooltipEnabled')
                : t('masterProfile.emptyState.importTooltipDisabled')
            }
          >
            <FileUp className="w-4 h-4" />
            {isImporting ? t('masterProfile.importing') : t('masterProfile.importFromCv')}
          </Button>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import ArrowLeft from 'lucide-react/dist/esm/icons/arrow-left';
import Briefcase from 'lucide-react/dist/esm/icons/briefcase';
import FileText from 'lucide-react/dist/esm/icons/file-text';
import GraduationCap from 'lucide-react/dist/esm/icons/graduation-cap';
import Loader2 from 'lucide-react/dist/esm/icons/loader-2';
import Plus from 'lucide-react/dist/esm/icons/plus';
import Save from 'lucide-react/dist/esm/icons/save';
import Trash2 from 'lucide-react/dist/esm/icons/trash-2';
import Wrench from 'lucide-react/dist/esm/icons/wrench';
import { Button } from '@/components/ui/button';
import { Card, CardDescription, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { MasterProfileEmptyState } from '@/components/master-profile/empty-state';
import { StringListEditor } from '@/components/master-profile/string-list-editor';
import { useTranslations } from '@/lib/i18n';
import {
  fetchMasterProfile,
  importCvToMasterProfile,
  updateMasterProfile,
} from '@/lib/api/master-profile';
import {
  EMPTY_MASTER_PROFILE,
  type MasterProfile,
  type MasterProfileEducation,
  type MasterProfileExperience,
  type MasterProfileProject,
} from '@/lib/types/master-profile';

function cloneProfile(profile: MasterProfile): MasterProfile {
  return JSON.parse(JSON.stringify(profile)) as MasterProfile;
}

function nextId(items: Array<{ id: number }>): number {
  return Math.max(0, ...items.map((item) => item.id)) + 1;
}

function normalizeNullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function splitLines(value: string): string[] {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
}

function SectionFrame({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="border-2 border-black bg-white shadow-[4px_4px_0px_0px_#000000]">
      <div className="space-y-6">
        <div className="space-y-2 border-b-2 border-black pb-4">
          <CardTitle className="text-2xl uppercase">{title}</CardTitle>
          <CardDescription className="text-xs uppercase text-gray-600">
            {description}
          </CardDescription>
        </div>
        {children}
      </div>
    </Card>
  );
}

export default function MasterProfilePage() {
  const { t } = useTranslations();
  const router = useRouter();
  const [profile, setProfile] = useState<MasterProfile | null>(null);
  const [lastSavedProfile, setLastSavedProfile] = useState<MasterProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [status, setStatus] = useState<{ type: 'error' | 'success'; message: string } | null>(null);
  const [storedResumeId, setStoredResumeId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadProfile = async () => {
      setIsLoading(true);
      if (typeof window !== 'undefined') {
        setStoredResumeId(localStorage.getItem('master_resume_id'));
      }
      try {
        const loadedProfile = await fetchMasterProfile();
        if (cancelled) {
          return;
        }
        setProfile(loadedProfile ? cloneProfile(loadedProfile) : null);
        setLastSavedProfile(loadedProfile ? cloneProfile(loadedProfile) : null);
      } catch (error) {
        if (!cancelled) {
          setStatus({
            type: 'error',
            message: error instanceof Error ? error.message : t('masterProfile.loadError'),
          });
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    loadProfile();
    return () => {
      cancelled = true;
    };
  }, [t]);

  const hasUnsavedChanges = useMemo(() => {
    if (!profile) {
      return false;
    }
    if (!lastSavedProfile) {
      return true;
    }
    return JSON.stringify(profile) !== JSON.stringify(lastSavedProfile);
  }, [profile, lastSavedProfile]);

  const updateProfile = (updater: (current: MasterProfile) => MasterProfile) => {
    setProfile((current) => {
      if (!current) {
        return current;
      }
      return updater(cloneProfile(current));
    });
  };

  const handleStartFromScratch = () => {
    const empty = cloneProfile(EMPTY_MASTER_PROFILE);
    setProfile(empty);
    setLastSavedProfile(null);
    setStatus(null);
  };

  const handleSave = async () => {
    if (!profile) {
      return;
    }
    setIsSaving(true);
    setStatus(null);
    try {
      const savedProfile = await updateMasterProfile(profile);
      setProfile(cloneProfile(savedProfile));
      setLastSavedProfile(cloneProfile(savedProfile));
      setStatus({ type: 'success', message: t('masterProfile.saveSuccess') });
    } catch (error) {
      setStatus({
        type: 'error',
        message: error instanceof Error ? error.message : t('masterProfile.saveError'),
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleImport = async () => {
    if (!storedResumeId) {
      setStatus({
        type: 'error',
        message: t('masterProfile.importNoResume'),
      });
      return;
    }
    setIsImporting(true);
    setStatus(null);
    try {
      const importedProfile = await importCvToMasterProfile(storedResumeId);
      setProfile(cloneProfile(importedProfile));
      setLastSavedProfile(cloneProfile(importedProfile));
      setStatus({ type: 'success', message: t('masterProfile.importSuccess') });
    } catch (error) {
      setStatus({
        type: 'error',
        message: error instanceof Error ? error.message : t('masterProfile.importError'),
      });
    } finally {
      setIsImporting(false);
    }
  };

  const handleAddExperience = () => {
    updateProfile((current) => ({
      ...current,
      workExperience: [
        ...current.workExperience,
        {
          id: nextId(current.workExperience),
          title: '',
          company: '',
          location: null,
          years: '',
          description: [],
          technologies: [],
        },
      ],
    }));
  };

  const handleAddProject = () => {
    updateProfile((current) => ({
      ...current,
      projects: [
        ...current.projects,
        {
          id: nextId(current.projects),
          name: '',
          role: '',
          years: '',
          github: null,
          website: null,
          description: [],
          technologies: [],
        },
      ],
    }));
  };

  const handleAddEducation = () => {
    updateProfile((current) => ({
      ...current,
      education: [
        ...current.education,
        {
          id: nextId(current.education),
          institution: '',
          degree: '',
          years: '',
          description: null,
        },
      ],
    }));
  };

  const handleExperienceChange = (
    id: number,
    updater: (item: MasterProfileExperience) => MasterProfileExperience
  ) => {
    updateProfile((current) => ({
      ...current,
      workExperience: current.workExperience.map((item) => (item.id === id ? updater(item) : item)),
    }));
  };

  const handleProjectChange = (
    id: number,
    updater: (item: MasterProfileProject) => MasterProfileProject
  ) => {
    updateProfile((current) => ({
      ...current,
      projects: current.projects.map((item) => (item.id === id ? updater(item) : item)),
    }));
  };

  const handleEducationChange = (
    id: number,
    updater: (item: MasterProfileEducation) => MasterProfileEducation
  ) => {
    updateProfile((current) => ({
      ...current,
      education: current.education.map((item) => (item.id === id ? updater(item) : item)),
    }));
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F0F0E8] p-6">
        <div className="mx-auto max-w-6xl border-2 border-black bg-white p-10 shadow-[4px_4px_0px_0px_#000000]">
          <div className="flex items-center gap-3 font-mono text-sm uppercase tracking-wider">
            <Loader2 className="w-4 h-4 animate-spin" />
            {t('common.loading')}
          </div>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-[#F0F0E8] p-6">
        <div className="mx-auto max-w-6xl space-y-6">
          <div className="flex items-center justify-between">
            <Button variant="outline" onClick={() => router.push('/dashboard')}>
              <ArrowLeft className="w-4 h-4" />
              {t('common.back')}
            </Button>
            <Link href="/tailor" className="font-mono text-xs uppercase text-blue-700 underline">
              {t('masterProfile.tailorLink')}
            </Link>
          </div>
          {status && (
            <div
              className={`border-2 p-4 font-mono text-xs uppercase tracking-wider ${
                status.type === 'error'
                  ? 'border-red-600 bg-red-50 text-red-700'
                  : 'border-green-700 bg-green-50 text-green-700'
              }`}
            >
              {status.message}
            </div>
          )}
          <MasterProfileEmptyState
            canImport={Boolean(storedResumeId)}
            isImporting={isImporting}
            onImport={handleImport}
            onStart={handleStartFromScratch}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F0F0E8] p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-2">
            <Button variant="outline" onClick={() => router.push('/dashboard')}>
              <ArrowLeft className="w-4 h-4" />
              {t('common.back')}
            </Button>
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-blue-700">
                {t('masterProfile.label')}
              </p>
              <h1 className="font-serif text-4xl font-bold uppercase">
                {t('masterProfile.title')}
              </h1>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" onClick={handleImport} disabled={isImporting}>
              {isImporting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              {isImporting ? t('masterProfile.importing') : t('masterProfile.importFromCv')}
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {isSaving ? t('common.saving') : t('masterProfile.saveMasterProfile')}
            </Button>
          </div>
        </div>

        {status && (
          <div
            className={`border-2 p-4 font-mono text-xs uppercase tracking-wider ${
              status.type === 'error'
                ? 'border-red-600 bg-red-50 text-red-700'
                : 'border-green-700 bg-green-50 text-green-700'
            }`}
          >
            {status.message}
          </div>
        )}

        {hasUnsavedChanges && (
          <div className="border-2 border-orange-500 bg-orange-50 p-4 font-mono text-xs uppercase tracking-wider text-orange-700">
            {t('masterProfile.unsavedChanges')}
          </div>
        )}

        <SectionFrame
          title={t('builder.personalInfo')}
          description={t('masterProfile.sections.personalInfo.description')}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label={t('masterProfile.fields.name')}
              value={profile.personalInfo.name}
              onChange={(value) =>
                updateProfile((current) => ({
                  ...current,
                  personalInfo: { ...current.personalInfo, name: value },
                }))
              }
            />
            <Field
              label={t('masterProfile.fields.title')}
              value={profile.personalInfo.title}
              onChange={(value) =>
                updateProfile((current) => ({
                  ...current,
                  personalInfo: { ...current.personalInfo, title: value },
                }))
              }
            />
            <Field
              label={t('masterProfile.fields.email')}
              value={profile.personalInfo.email}
              onChange={(value) =>
                updateProfile((current) => ({
                  ...current,
                  personalInfo: { ...current.personalInfo, email: value },
                }))
              }
            />
            <Field
              label={t('masterProfile.fields.phone')}
              value={profile.personalInfo.phone}
              onChange={(value) =>
                updateProfile((current) => ({
                  ...current,
                  personalInfo: { ...current.personalInfo, phone: value },
                }))
              }
            />
            <Field
              label={t('builder.genericItemForm.fields.location')}
              value={profile.personalInfo.location}
              onChange={(value) =>
                updateProfile((current) => ({
                  ...current,
                  personalInfo: { ...current.personalInfo, location: value },
                }))
              }
            />
            <Field
              label={t('builder.forms.projects.fields.website')}
              value={profile.personalInfo.website ?? ''}
              onChange={(value) =>
                updateProfile((current) => ({
                  ...current,
                  personalInfo: { ...current.personalInfo, website: normalizeNullable(value) },
                }))
              }
            />
            <Field
              label={t('masterProfile.fields.linkedin')}
              value={profile.personalInfo.linkedin ?? ''}
              onChange={(value) =>
                updateProfile((current) => ({
                  ...current,
                  personalInfo: { ...current.personalInfo, linkedin: normalizeNullable(value) },
                }))
              }
            />
            <Field
              label={t('masterProfile.fields.github')}
              value={profile.personalInfo.github ?? ''}
              onChange={(value) =>
                updateProfile((current) => ({
                  ...current,
                  personalInfo: { ...current.personalInfo, github: normalizeNullable(value) },
                }))
              }
            />
            <div className="space-y-2 md:col-span-2">
              <Label className="font-mono text-xs uppercase tracking-wider text-gray-600">
                {t('builder.summary')}
              </Label>
              <Textarea
                value={profile.personalInfo.summary}
                onChange={(event) =>
                  updateProfile((current) => ({
                    ...current,
                    personalInfo: { ...current.personalInfo, summary: event.target.value },
                  }))
                }
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.stopPropagation();
                  }
                }}
                className="min-h-[160px] border-2 border-black bg-white font-sans"
                placeholder={t('masterProfile.fields.summaryPlaceholder')}
              />
            </div>
          </div>
        </SectionFrame>

        <SectionFrame
          title={t('masterProfile.sections.workExperience.title')}
          description={t('masterProfile.sections.workExperience.description')}
        >
          <div className="space-y-6">
            {profile.workExperience.map((item) => (
              <div key={item.id} className="space-y-4 border-2 border-black bg-[#F8F7F1] p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-blue-700">
                    <Briefcase className="w-4 h-4" />
                    {t('masterProfile.sections.workExperience.item', { id: item.id })}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() =>
                      updateProfile((current) => ({
                        ...current,
                        workExperience: current.workExperience.filter(
                          (experience) => experience.id !== item.id
                        ),
                      }))
                    }
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <Field
                    label={t('builder.forms.experience.fields.jobTitle')}
                    value={item.title}
                    onChange={(value) =>
                      handleExperienceChange(item.id, (current) => ({ ...current, title: value }))
                    }
                  />
                  <Field
                    label={t('builder.forms.experience.fields.company')}
                    value={item.company}
                    onChange={(value) =>
                      handleExperienceChange(item.id, (current) => ({
                        ...current,
                        company: value,
                      }))
                    }
                  />
                  <Field
                    label={t('builder.genericItemForm.fields.location')}
                    value={item.location ?? ''}
                    onChange={(value) =>
                      handleExperienceChange(item.id, (current) => ({
                        ...current,
                        location: normalizeNullable(value),
                      }))
                    }
                  />
                  <Field
                    label={t('builder.genericItemForm.fields.years')}
                    value={item.years}
                    onChange={(value) =>
                      handleExperienceChange(item.id, (current) => ({ ...current, years: value }))
                    }
                  />
                </div>
                <StringListEditor
                  id={`experience-tech-${item.id}`}
                  label={t('masterProfile.fields.technologies')}
                  values={item.technologies}
                  placeholder={`Python\nFastAPI\nDocker`}
                  onChange={(values) =>
                    handleExperienceChange(item.id, (current) => ({
                      ...current,
                      technologies: values,
                    }))
                  }
                />
                <div className="space-y-2">
                  <Label className="font-mono text-xs uppercase tracking-wider text-gray-600">
                    {t('masterProfile.sections.workExperience.descriptionBullets')}
                  </Label>
                  <Textarea
                    value={item.description.join('\n')}
                    onChange={(event) =>
                      handleExperienceChange(item.id, (current) => ({
                        ...current,
                        description: splitLines(event.target.value),
                      }))
                    }
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.stopPropagation();
                      }
                    }}
                    className="min-h-[160px] border-2 border-black bg-white font-sans"
                    placeholder={t('masterProfile.sections.workExperience.descriptionPlaceholder')}
                  />
                </div>
              </div>
            ))}
            <Button variant="outline" onClick={handleAddExperience}>
              <Plus className="w-4 h-4" />
              {t('masterProfile.sections.workExperience.addButton')}
            </Button>
          </div>
        </SectionFrame>

        <SectionFrame
          title={t('builder.projects')}
          description={t('masterProfile.sections.projects.description')}
        >
          <div className="space-y-6">
            {profile.projects.map((item) => (
              <div key={item.id} className="space-y-4 border-2 border-black bg-[#F8F7F1] p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-blue-700">
                    <FileText className="w-4 h-4" />
                    {t('masterProfile.sections.projects.item', { id: item.id })}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() =>
                      updateProfile((current) => ({
                        ...current,
                        projects: current.projects.filter((project) => project.id !== item.id),
                      }))
                    }
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <Field
                    label={t('builder.forms.projects.fields.projectName')}
                    value={item.name}
                    onChange={(value) =>
                      handleProjectChange(item.id, (current) => ({ ...current, name: value }))
                    }
                  />
                  <Field
                    label={t('builder.forms.projects.fields.role')}
                    value={item.role}
                    onChange={(value) =>
                      handleProjectChange(item.id, (current) => ({ ...current, role: value }))
                    }
                  />
                  <Field
                    label={t('builder.genericItemForm.fields.years')}
                    value={item.years}
                    onChange={(value) =>
                      handleProjectChange(item.id, (current) => ({ ...current, years: value }))
                    }
                  />
                  <Field
                    label={t('masterProfile.fields.github')}
                    value={item.github ?? ''}
                    onChange={(value) =>
                      handleProjectChange(item.id, (current) => ({
                        ...current,
                        github: normalizeNullable(value),
                      }))
                    }
                  />
                  <div className="md:col-span-2">
                    <Field
                      label={t('builder.forms.projects.fields.website')}
                      value={item.website ?? ''}
                      onChange={(value) =>
                        handleProjectChange(item.id, (current) => ({
                          ...current,
                          website: normalizeNullable(value),
                        }))
                      }
                    />
                  </div>
                </div>
                <StringListEditor
                  id={`project-tech-${item.id}`}
                  label={t('masterProfile.fields.technologies')}
                  values={item.technologies}
                  placeholder={`Next.js\nTypeScript\nPostgreSQL`}
                  onChange={(values) =>
                    handleProjectChange(item.id, (current) => ({
                      ...current,
                      technologies: values,
                    }))
                  }
                />
                <div className="space-y-2">
                  <Label className="font-mono text-xs uppercase tracking-wider text-gray-600">
                    {t('masterProfile.sections.projects.descriptionBullets')}
                  </Label>
                  <Textarea
                    value={item.description.join('\n')}
                    onChange={(event) =>
                      handleProjectChange(item.id, (current) => ({
                        ...current,
                        description: splitLines(event.target.value),
                      }))
                    }
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.stopPropagation();
                      }
                    }}
                    className="min-h-[160px] border-2 border-black bg-white font-sans"
                    placeholder={t('masterProfile.sections.projects.descriptionPlaceholder')}
                  />
                </div>
              </div>
            ))}
            <Button variant="outline" onClick={handleAddProject}>
              <Plus className="w-4 h-4" />
              {t('builder.forms.projects.addProject')}
            </Button>
          </div>
        </SectionFrame>

        <SectionFrame
          title={t('builder.education')}
          description={t('masterProfile.sections.education.description')}
        >
          <div className="space-y-6">
            {profile.education.map((item) => (
              <div key={item.id} className="space-y-4 border-2 border-black bg-[#F8F7F1] p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-blue-700">
                    <GraduationCap className="w-4 h-4" />
                    {t('masterProfile.sections.education.item', { id: item.id })}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() =>
                      updateProfile((current) => ({
                        ...current,
                        education: current.education.filter((entry) => entry.id !== item.id),
                      }))
                    }
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <Field
                    label={t('builder.forms.education.fields.institution')}
                    value={item.institution}
                    onChange={(value) =>
                      handleEducationChange(item.id, (current) => ({
                        ...current,
                        institution: value,
                      }))
                    }
                  />
                  <Field
                    label={t('builder.forms.education.fields.degree')}
                    value={item.degree}
                    onChange={(value) =>
                      handleEducationChange(item.id, (current) => ({ ...current, degree: value }))
                    }
                  />
                  <Field
                    label={t('builder.genericItemForm.fields.years')}
                    value={item.years}
                    onChange={(value) =>
                      handleEducationChange(item.id, (current) => ({ ...current, years: value }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label className="font-mono text-xs uppercase tracking-wider text-gray-600">
                    {t('builder.forms.education.fields.description')}
                  </Label>
                  <Textarea
                    value={item.description ?? ''}
                    onChange={(event) =>
                      handleEducationChange(item.id, (current) => ({
                        ...current,
                        description: normalizeNullable(event.target.value),
                      }))
                    }
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.stopPropagation();
                      }
                    }}
                    className="min-h-[100px] border-2 border-black bg-white font-sans"
                    placeholder={t('masterProfile.sections.education.descriptionPlaceholder')}
                  />
                </div>
              </div>
            ))}
            <Button variant="outline" onClick={handleAddEducation}>
              <Plus className="w-4 h-4" />
              {t('masterProfile.sections.education.addButton')}
            </Button>
          </div>
        </SectionFrame>

        <SectionFrame
          title={t('masterProfile.sections.skills.title')}
          description={t('masterProfile.sections.skills.description')}
        >
          <div className="grid gap-6 lg:grid-cols-3">
            <StringListEditor
              id="master-profile-skills"
              label={t('builder.skills')}
              values={profile.skills}
              placeholder={`Python\nFastAPI\nDocker`}
              onChange={(values) => updateProfile((current) => ({ ...current, skills: values }))}
            />
            <StringListEditor
              id="master-profile-languages"
              label={t('builder.languages')}
              values={profile.languages}
              placeholder={`English\nFrench`}
              onChange={(values) => updateProfile((current) => ({ ...current, languages: values }))}
            />
            <StringListEditor
              id="master-profile-certifications"
              label={t('builder.certifications')}
              values={profile.certifications}
              placeholder={`AWS Solutions Architect\nAzure Fundamentals`}
              onChange={(values) =>
                updateProfile((current) => ({ ...current, certifications: values }))
              }
            />
          </div>
          <div className="flex items-center gap-2 border-2 border-black bg-[#F8F7F1] p-4 font-mono text-xs uppercase tracking-wider text-gray-700">
            <Wrench className="w-4 h-4 text-blue-700" />
            {t('masterProfile.sections.skills.tailoringNote')}
          </div>
        </SectionFrame>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label className="font-mono text-xs uppercase tracking-wider text-gray-600">{label}</Label>
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-11 border-2 border-black bg-white"
      />
    </div>
  );
}

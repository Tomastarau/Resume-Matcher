export interface MasterProfilePersonalInfo {
  name: string;
  title: string;
  email: string;
  phone: string;
  location: string;
  website: string | null;
  linkedin: string | null;
  github: string | null;
  summary: string;
}

export interface MasterProfileExperience {
  id: number;
  title: string;
  company: string;
  location: string | null;
  years: string;
  description: string[];
  technologies: string[];
}

export interface MasterProfileProject {
  id: number;
  name: string;
  role: string;
  years: string;
  github: string | null;
  website: string | null;
  description: string[];
  technologies: string[];
}

export interface MasterProfileEducation {
  id: number;
  institution: string;
  degree: string;
  years: string;
  description: string | null;
}

export interface MasterProfile {
  personalInfo: MasterProfilePersonalInfo;
  workExperience: MasterProfileExperience[];
  projects: MasterProfileProject[];
  education: MasterProfileEducation[];
  skills: string[];
  languages: string[];
  certifications: string[];
}

export const EMPTY_MASTER_PROFILE: MasterProfile = {
  personalInfo: {
    name: '',
    title: '',
    email: '',
    phone: '',
    location: '',
    website: null,
    linkedin: null,
    github: null,
    summary: '',
  },
  workExperience: [],
  projects: [],
  education: [],
  skills: [],
  languages: [],
  certifications: [],
};

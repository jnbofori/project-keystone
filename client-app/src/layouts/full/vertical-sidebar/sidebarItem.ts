import { DashboardIcon, FolderIcon, BuildingIcon } from 'vue-tabler-icons';

export interface menu {
  header?: string;
  title?: string;
  icon?: object;
  to?: string;
  divider?: boolean;
  chip?: string;
  chipColor?: string;
  chipVariant?: string;
  chipIcon?: string;
  children?: menu[];
  disabled?: boolean;
  type?: string;
  subCaption?: string;
}

const sidebarItem: menu[] = [
  { header: 'Keystone' },
  {
    title: 'Dashboard',
    icon: DashboardIcon,
    to: '/dashboard/default'
  },
  {
    title: 'Organization',
    icon: BuildingIcon,
    to: '/settings/organization'
  },
  {
    title: 'Projects',
    icon: FolderIcon,
    to: '/projects'
  }
];

export default sidebarItem;

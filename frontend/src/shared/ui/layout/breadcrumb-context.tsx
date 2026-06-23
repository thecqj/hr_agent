import { createContext, useContext, useState } from "react";
import type { Dispatch, SetStateAction } from "react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbContextType {
  items: BreadcrumbItem[];
  setItems: Dispatch<SetStateAction<BreadcrumbItem[]>>;
}

const BreadcrumbContext = createContext<BreadcrumbContextType>({
  items: [],
  setItems: () => {},
});

export function BreadcrumbProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<BreadcrumbItem[]>([]);
  return (
    <BreadcrumbContext.Provider value={{ items, setItems }}>
      {children}
    </BreadcrumbContext.Provider>
  );
}

export function useBreadcrumb() {
  return useContext(BreadcrumbContext);
}

import { Button } from "@/components/ui/button";

interface Category<T extends string> {
  key: T;
  label: string;
}

interface CategoryTabsProps<T extends string> {
  categories: Category<T>[];
  activeKey: T;
  onSelect: (key: T) => void;
}

export function CategoryTabs<T extends string = string>({
  categories,
  activeKey,
  onSelect,
}: CategoryTabsProps<T>) {
  return (
    <div className="flex flex-wrap gap-2">
      {categories.map((cat) => (
        <Button
          key={cat.key}
          variant={activeKey === cat.key ? "default" : "outline"}
          size="sm"
          onClick={() => onSelect(cat.key)}
        >
          {cat.label}
        </Button>
      ))}
    </div>
  );
}

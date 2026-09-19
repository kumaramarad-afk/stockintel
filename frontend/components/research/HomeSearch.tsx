"use client";

import { SearchBox } from "@/components/SearchBox";

type HomeSearchProps = {
  className?: string;
  buttonLabel?: string;
  placeholder?: string;
};

export function HomeSearch({
  className,
  buttonLabel = "Open report",
  placeholder = "Search any US stock — ticker or company (Micron, SanDisk, AAPL…)",
}: HomeSearchProps) {
  return (
    <SearchBox
      className={className}
      buttonLabel={buttonLabel}
      placeholder={placeholder}
      showButton
      debounceMs={300}
    />
  );
}

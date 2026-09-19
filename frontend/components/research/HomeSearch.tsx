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
  placeholder = "Search any ticker or company (Apple, AAPL, NVIDIA…)",
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

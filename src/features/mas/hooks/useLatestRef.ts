// Manages use latest ref behavior.
import { useEffect, useRef } from 'react';

// Manages latest ref.
export function useLatestRef<T>(value: T) {
  const ref = useRef(value);

// Manages effect.
  useEffect(() => {
    ref.current = value;
  }, [value]);

  return ref;
}

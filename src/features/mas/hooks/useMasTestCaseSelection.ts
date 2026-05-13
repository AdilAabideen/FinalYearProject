// Manages use MAS test case selection behavior.
import { useEffect, useMemo, useState } from 'react';
import type { MasTestCaseRead } from '../../../types/masTests';
import type { MasTestTabKey, TestCaseTabKey } from '../utils/masTestCases';

// Manages MAS test case selection.
export function useMasTestCaseSelection(testCases: MasTestCaseRead[]) {
  const [selectedTestCase, setSelectedTestCase] = useState<MasTestCaseRead | null>(null);
  const [selectedTestCaseIds, setSelectedTestCaseIds] = useState<string[]>([]);
  const [showCaseWorkspace, setShowCaseWorkspace] = useState(false);
  const [activeTab, setActiveTab] = useState<TestCaseTabKey>('test_case');
  const [activeMasTab, setActiveMasTab] = useState<MasTestTabKey>('test');

// Manages effect.
  useEffect(() => {
// Sets selected test case IDS.
    setSelectedTestCaseIds((prev) =>
// Handles some.
// Handles filter.
      prev.length ? prev.filter((id) => testCases.some((testCase) => testCase.id === id)) : [],
    );
// Sets selected test case.
    setSelectedTestCase((prev) => {
// Handles some.
      if (prev && testCases.some((testCase) => testCase.id === prev.id)) {
        return prev;
      }
      return testCases[0] ?? null;
    });
  }, [testCases]);

  const visibleTestCases = useMemo(
// Manages memo.
    () =>
      selectedTestCaseIds.length > 0
// Handles filter.
        ? testCases.filter((testCase) => selectedTestCaseIds.includes(testCase.id))
        : [],
    [selectedTestCaseIds, testCases],
  );

// Manages effect.
  useEffect(() => {
    if (!showCaseWorkspace) return;

// Sets selected test case.
    setSelectedTestCase((prev) => {
// Handles some.
      if (prev && visibleTestCases.some((testCase) => testCase.id === prev.id)) {
        return prev;
      }
      return visibleTestCases[0] ?? null;
    });
  }, [showCaseWorkspace, visibleTestCases]);

// Toggles test case selection.
  function toggleTestCaseSelection(testCaseId: string) {
// Sets selected test case IDS.
    setSelectedTestCaseIds((prev) =>
      prev.includes(testCaseId)
// Handles filter.
        ? prev.filter((id) => id !== testCaseId)
        : [...prev, testCaseId],
    );
  }

// Toggles select all test cases.
  function toggleSelectAllTestCases() {
// Sets selected test case IDS.
    setSelectedTestCaseIds((prev) =>
// Maps logic.
      prev.length === testCases.length ? [] : testCases.map((testCase) => testCase.id),
    );
  }

  return {
    selectedTestCase,
    setSelectedTestCase,
    selectedTestCaseId: selectedTestCase?.id ?? null,
    selectedTestCaseIds,
    showCaseWorkspace,
    activeTab,
    activeMasTab,
    visibleTestCases,
    allSelected: testCases.length > 0 && selectedTestCaseIds.length === testCases.length,
    setActiveTab,
    setActiveMasTab,
    toggleTestCaseSelection,
    toggleSelectAllTestCases,
// Opens selected cases.
    openSelectedCases: () => setShowCaseWorkspace(true),
  };
}

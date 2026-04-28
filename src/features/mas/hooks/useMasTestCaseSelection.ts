import { useEffect, useMemo, useState } from 'react';
import type { MasTestCaseRead } from '../../../types/masTests';
import type { MasTestTabKey, TestCaseTabKey } from '../utils/masTestCases';

export function useMasTestCaseSelection(testCases: MasTestCaseRead[]) {
  const [selectedTestCase, setSelectedTestCase] = useState<MasTestCaseRead | null>(null);
  const [selectedTestCaseIds, setSelectedTestCaseIds] = useState<string[]>([]);
  const [showCaseWorkspace, setShowCaseWorkspace] = useState(false);
  const [activeTab, setActiveTab] = useState<TestCaseTabKey>('test_case');
  const [activeMasTab, setActiveMasTab] = useState<MasTestTabKey>('test');

  useEffect(() => {
    setSelectedTestCaseIds((prev) =>
      prev.length ? prev.filter((id) => testCases.some((testCase) => testCase.id === id)) : [],
    );
    setSelectedTestCase((prev) => {
      if (prev && testCases.some((testCase) => testCase.id === prev.id)) {
        return prev;
      }
      return testCases[0] ?? null;
    });
  }, [testCases]);

  const visibleTestCases = useMemo(
    () =>
      selectedTestCaseIds.length > 0
        ? testCases.filter((testCase) => selectedTestCaseIds.includes(testCase.id))
        : [],
    [selectedTestCaseIds, testCases],
  );

  useEffect(() => {
    if (!showCaseWorkspace) return;

    setSelectedTestCase((prev) => {
      if (prev && visibleTestCases.some((testCase) => testCase.id === prev.id)) {
        return prev;
      }
      return visibleTestCases[0] ?? null;
    });
  }, [showCaseWorkspace, visibleTestCases]);

  function toggleTestCaseSelection(testCaseId: string) {
    setSelectedTestCaseIds((prev) =>
      prev.includes(testCaseId)
        ? prev.filter((id) => id !== testCaseId)
        : [...prev, testCaseId],
    );
  }

  function toggleSelectAllTestCases() {
    setSelectedTestCaseIds((prev) =>
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
    openSelectedCases: () => setShowCaseWorkspace(true),
  };
}

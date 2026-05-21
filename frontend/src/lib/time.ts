/**
 * Parses and validates a time string in 24h (HH:MM) or AM/PM format.
 * Returns an object indicating validity, total minutes since midnight, and a normalized HH:MM string.
 */
export function parseAndValidateTime(timeStr: string): { valid: boolean; minutes: number; normalized: string } {
  if (!timeStr) return { valid: false, minutes: 0, normalized: '' };
  
  const clean = timeStr.trim().toLowerCase().replace(/\s+/g, ' ');
  
  // Handle standard 24h format HH:MM
  const match24 = clean.match(/^(\d{1,2}):(\d{2})$/);
  if (match24) {
    const h = parseInt(match24[1], 10);
    const m = parseInt(match24[2], 10);
    if (h >= 0 && h < 24 && m >= 0 && m < 60) {
      const padH = String(h).padStart(2, '0');
      const padM = String(m).padStart(2, '0');
      return { valid: true, minutes: h * 60 + m, normalized: `${padH}:${padM}` };
    }
  }
  
  // Handle formats with AM/PM (could be a. m., p. m., a.m., p.m., am, pm, etc.)
  const matchAmpm = clean.match(/^(\d{1,2}):(\d{2})\s*([ap](?:\.?,?\s*m?\.?)?)/i);
  if (matchAmpm) {
    let h = parseInt(matchAmpm[1], 10);
    const m = parseInt(matchAmpm[2], 10);
    const periodStr = matchAmpm[3];
    
    const isPm = periodStr.includes('p');
    const isAm = periodStr.includes('a');
    
    if (h >= 1 && h <= 12 && m >= 0 && m < 60 && (isAm || isPm)) {
      if (isPm && h < 12) {
        h += 12;
      } else if (isAm && h === 12) {
        h = 0;
      }
      const padH = String(h).padStart(2, '0');
      const padM = String(m).padStart(2, '0');
      return { valid: true, minutes: h * 60 + m, normalized: `${padH}:${padM}` };
    }
  }
  
  return { valid: false, minutes: 0, normalized: '' };
}

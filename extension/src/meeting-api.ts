interface MeetingCreatePayload {
  title: string;
  meet_url: string;
}

interface MeetingCreateResponse {
  id: string;
}

const jsonHeaders = { "Content-Type": "application/json" };

export const createMeeting = async (gatewayHttpUrl: string, payload: MeetingCreatePayload): Promise<string> => {
  const response = await fetch(`${gatewayHttpUrl}/meetings`, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = (await response.json()) as MeetingCreateResponse;
  return data.id;
};

export const finalizeMeeting = async (gatewayHttpUrl: string, meetingId: string): Promise<void> => {
  await fetch(`${gatewayHttpUrl}/meetings/${meetingId}`, {
    method: "PATCH",
    headers: jsonHeaders,
    body: JSON.stringify({ status: "final" }),
  });
};

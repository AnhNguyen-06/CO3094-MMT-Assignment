"""CUBIC growth and congestion-event state.

Slides 123, 126-127 motivate SS and cubic CA. Equations/units and target
bounds: RFC 9438 sections 4.1-4.5; classic SS is the project's choice.
Recovery retransmission is owned by the Reliability sender.
"""
class CubicController:
    C = 0.4
    BETA = 0.7

    def __init__(self, mss, fast_convergence=True):
        self.mss = mss
        self.fast_convergence = fast_convergence
        # cwnd and ssthresh remain solely in the connection record, in bytes.
        # These additional CUBIC variables use SMSS-sized segments and seconds.
        self.w_max = None
        self.cwnd_prior = None
        self.w_est = None
        self.k = 0.0
        self.elapsed = 0.0
        self.last_update = None
        self.active = False

    def on_loss(self, cwnd, flight_size, now, timeout=False):
        """RFC 9438 4.6-4.8: windows in bytes, W_max in segments.

        Use FlightSize for threshold; do not substitute an inflated recovery
        window. Fast convergence is configurable (disable for isolated flows).
        """
        window = cwnd / self.mss
        self.cwnd_prior = window
        if (self.fast_convergence and self.w_max is not None
                and window < self.w_max):
            self.w_max = window * (1 + self.BETA) / 2
        else:
            self.w_max = window
        threshold = max(2 * self.mss, flight_size * self.BETA)
        self.pause(now)
        self.w_est = None
        self.elapsed = 0.0
        if timeout:
            # RFC 9438 4.8: first CA after RTO starts a fresh K=0 epoch.
            self.w_max = None
            self.k = 0.0
            return float(self.mss), threshold
        return threshold, threshold

    def pause(self, now):
        """Exclude application/receiver limited intervals from the cubic clock."""
        if self.active:
            self.elapsed += max(0.0, now - self.last_update)
        self.last_update = now
        self.active = False

    def resume(self, now):
        """Resume an existing epoch when transmission restarts after idle."""
        if self.w_est is not None and not self.active:
            self.last_update = now
            self.active = True

    def update_clock(self, now, eligible, transmitting=False):
        """RFC 9438 4.2/5.8: pause immediately; resume on actual data send.

        A window-opening ACK alone does not establish an active transmission.
        Repeated window updates/probes cannot count the paused interval twice.
        """
        if not eligible:
            self.pause(now)
        elif transmitting:
            self.resume(now)

    def on_ack(self, cwnd, ssthresh, acknowledged, rtt, now, eligible):
        if acknowledged <= 0 or not eligible:
            self.update_clock(now, False)
            return cwnd
        if cwnd < ssthresh:
            # Classic SS: at most SMSS bytes per new ACK (partial ACK aware).
            self.pause(now)
            return cwnd + min(acknowledged, self.mss)
        if rtt is None or rtt <= 0:
            self.pause(now)
            return cwnd  # no invented RTT for the cubic time function
        window = cwnd / self.mss
        if self.w_est is None:
            # First CA epoch: no loss has established a previous W_max yet.
            if self.w_max is None:
                self.w_max = window
                self.cwnd_prior = window
            self.w_est = window
            distance = (self.w_max - window) / self.C
            self.k = abs(distance) ** (1 / 3) * (1 if distance >= 0 else -1)
            self.elapsed = 0.0
            self.active = True
        elif self.active:
            self.elapsed += max(0.0, now - self.last_update)
        self.last_update = now
        w_cubic = self.C * (self.elapsed - self.k) ** 3 + self.w_max
        target = self.C * (self.elapsed + rtt - self.k) ** 3 + self.w_max
        target = min(1.5 * window, max(window, target))
        alpha = 3 * (1 - self.BETA) / (1 + self.BETA)
        if self.w_est >= self.cwnd_prior:
            alpha = 1.0
        self.w_est += alpha * (acknowledged / self.mss) / window
        if w_cubic < self.w_est:
            result = max(window, self.w_est)
        else:
            # RFC 9438 4.4/4.5: one increment per new ACK. Fractional
            # segments_acked is used separately in the Reno-friendly estimate.
            result = window + (target - window) / window
        return result * self.mss

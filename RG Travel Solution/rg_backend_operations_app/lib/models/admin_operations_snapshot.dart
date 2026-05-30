class AdminOperationsSnapshot {
  const AdminOperationsSnapshot({
    this.liveTrips = 0,
    this.driverRequests = 0,
    this.employeeRequests = 0,
    this.driverChanges = 0,
    this.employeeChanges = 0,
    this.swapRequests = 0,
    this.tripCancels = 0,
    this.absenceRequests = 0,
    this.drivers = 0,
    this.employees = 0,
    this.onlineDrivers = 0,
    this.sos = 0,
    this.helpdesk = 0,
  });

  final int liveTrips;
  final int driverRequests;
  final int employeeRequests;
  final int driverChanges;
  final int employeeChanges;
  final int swapRequests;
  final int tripCancels;
  final int absenceRequests;
  final int drivers;
  final int employees;
  final int onlineDrivers;
  final int sos;
  final int helpdesk;

  int get pendingApprovals =>
      driverRequests +
      employeeRequests +
      driverChanges +
      employeeChanges +
      swapRequests +
      tripCancels +
      absenceRequests;
}

/*
 * =================================================================
 * StArranja Database Setup Script
 * =================================================================
 * This script creates the database, collections, validation schemas,
 * and all performance and business rule indexes.
 *
 * This script is executed with the command:
 * mongosh "mongodb-url/starranja" --file database-mongo-setup.js
 */


print("Starting the StArranja database setup");

/*
 * =================================================================
 * Collection: clients
 * =================================================================
 */
db.createCollection("clients");

db.clients.createIndex(
  { nif: 1 },
  { unique: true }
);
db.clients.createIndex(
  { phone: 1 }
);
db.clients.createIndex(
  { email: 1 },
  { unique: true, partialFilterExpression: { email: { $exists: true } } }
);

print("Collection 'clients' created with indexes.");

/*
 * =================================================================
 * Collection: vehicles
 * =================================================================
 */
db.createCollection("vehicles");

db.vehicles.createIndex(
  { licensePlate: 1 },
  { unique: true }
);
db.vehicles.createIndex(
  { clientId: 1 }
);
db.vehicles.createIndex(
  { vin: 1 },
  {
    unique: true,
    partialFilterExpression: { vin: { $exists: true } }
  }
);

print("Collection 'vehicles' created with indexes.");

/*
 * =================================================================
 * Collection: workOrders
 * =================================================================
 */
db.createCollection("workOrders");

// --- Indexes of workOrders ---

// Index for Business Rule RB02
db.workOrders.createIndex(
  { vehicleId: 1 },
  {
    unique: true,
    partialFilterExpression: {
        isActive: true
    }
  }
);
// Index for searching by number
db.workOrders.createIndex(
  { workOrderNumber: 1 },
  { unique: true }
);
// Index for Dashboard by status
db.workOrders.createIndex(
  { status: 1 }
);
// Index for Dashboard by entry date
db.workOrders.createIndex(
  { entryDate: -1 }
);
// Composite Index for Dashboard (status + data)
db.workOrders.createIndex(
  { status: 1, entryDate: -1 }
);
// Index for customer history
db.workOrders.createIndex(
  { clientId: 1 }
);
// Index for Mechanics Dashboard
db.workOrders.createIndex(
  { mechanicsIds: 1 }
);

print("Collection 'workOrders' created with indexes.");

/*
 * =================================================================
 * Collection: invoices
 * =================================================================
 */
db.createCollection("invoices");

db.invoices.createIndex(
  { invoiceNumber: 1 },
  { unique: true }
);
db.invoices.createIndex(
  { workOrderId: 1 },
  { unique: true }
);
db.invoices.createIndex(
  { clientId: 1 }
);
db.invoices.createIndex(
  { invoiceDate: -1 }
);

print("Collection 'invoices' created with indexes.");

/*
 * =================================================================
 * Collection: appointments
 * =================================================================
 */

db.createCollection("appointments");

db.appointments.createIndex({ appointmentDate: -1 });
db.appointments.createIndex({ clientId: 1 });
db.appointments.createIndex({ status: 1, appointmentDate: 1 });

print("Collection 'appointments' created successfully.");

/*
 * =================================================================
 * Collection: supplierOrders
 * =================================================================
 */

db.createCollection("supplierOrders");

// Indexes
db.supplierOrders.createIndex({ workOrderId: 1 }, { sparse: true }); // Sparse index automatically handled by Mongo if null
db.supplierOrders.createIndex({status: 1});
db.supplierOrders.createIndex({createdAt: -1}); // Newest orders first
db.supplierOrders.createIndex({supplierName: 1});

print("[✓] Collection 'supplierOrders' created successfully.");


print("\n--- StArranja Database Setup Complete ---");
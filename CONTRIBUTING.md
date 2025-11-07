## Development Workflow

Here we follow a test driven development sequence to maintain code organization and prevent dependencies, always 
writing tests before implementing features to promote code design and minimize bugs:

1. **Develop [Models](src/models)** - Start by creating data models and schemas (you can check the DB diagrams [here](docs/))
   - Write validation tests if applicable
   - Define your model structure

2. **Develop [Database Interfacing Files](src/repository)** - Build the interaction layer between our backend and the database
   - Write DB tests (using fixtures/test DB)
   - Tests FAIL
   - Implement CRUD operations against the existing databases (using the previously created models)
   - Tests PASS
   - Refactor if needed
   
3. **Develop [Routes](src/routes)** - Implement API endpoints after models and DB layer are ready
   - Write route tests (mock DB layer)
   - Tests FAIL
   - Implement the endpoints (taking advantage of the developed DB interfacing files and the models)
   - Tests PASS
   - Refactor if needed
   
This order ensures a steady and compatible workflow, because the models represent the DB tables, while the DB interfacing
 layer depends on the models and interacts with the DB itself, and the routes depending on both the models and the DB interfaces.
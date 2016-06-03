# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2016, Oracle and/or its affiliates. All rights reserved.

# MySQL Connector/Python is licensed under the terms of the GPLv2
# <http://www.gnu.org/licenses/old-licenses/gpl-2.0.html>, like most
# MySQL Connectors. There are special exceptions to the terms and
# conditions of the GPLv2 as it is applied to this software, see the
# FOSS License Exception
# <http://www.mysql.com/about/legal/licensing/foss-exception.html>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

from .statement import (FindStatement, AddStatement, RemoveStatement, ModifyStatement,
                        SelectStatement, InsertStatement, DeleteStatement, UpdateStatement,
                        CreateCollectionIndexStatement, DropCollectionIndexStatement)


_COUNT_TABLES_QUERY = ("SELECT COUNT(*) FROM information_schema.tables "
                       "WHERE table_schema = '{0}' AND table_name = '{1}'")
_COUNT_SCHEMAS_QUERY = ("SELECT COUNT(*) FROM information_schema.schemata "
                        "WHERE schema_name like '{0}'")
_COUNT_QUERY = "SELECT COUNT(*) FROM `{0}`.`{1}`"
_DROP_TABLE_QUERY = "DROP TABLE IF EXISTS `{0}`.`{1}`"


class DatabaseObject(object):
    """Provides base functionality for database objects.

    Args:
        schema (mysqlx.Schema): The Schema object.
        name (str): The database object name.
    """
    def __init__(self, schema, name):
        self._schema = schema
        self._name = name
        self._connection = self._schema.get_session()._connection

    @property
    def schema(self):
        """:class:`mysqlx.Schema`: The Schema object.
        """
        return self._schema

    @property
    def name(self):
        """str: The name of this database object.
        """
        return self._name

    def get_schema(self):
        """Returns the Schema object of this database object.

        Returns:
            mysqlx.Schema: The Schema object.
        """
        return self._schema

    def get_name(self):
        """Returns the name of this database object.

        Returns:
            str: The name of this database object.
        """
        return self._name


class Schema(DatabaseObject):
    """A client-side representation of a database schema. Provides access to
    the schema contents.

    Args:
        session (mysqlx.XSession): Session object.
        name (str): The Schema name.
    """
    def __init__(self, session, name):
        self._session = session
        super(Schema, self).__init__(self, name)

    def exists_in_database(self):
        """Verifies if this object exists in the database.

        Returns:
            bool: `True` if object exists in database.
        """
        sql = _COUNT_SCHEMAS_QUERY.format(self._name)
        return self._connection.execute_sql_scalar(sql) == 1

    def get_session(self):
        """Returns the session of this Schema object.

        Returns:
            mysqlx.Session: The Session object.
        """
        return self._session

    def get_collections(self):
        """Returns a list of collections for this schema.

        Returns:
            list: List of Collection objects.
        """
        rows = self._connection.get_row_result("list_objects", self._name)
        rows.fetch_all()
        collections = []
        for row in rows:
            if row.get_string("type") != "COLLECTION":
                continue
            collection = Collection(self, row.get_string("name"))
            collections.append(collection)
        return collections

    def get_tables(self):
        """Returns a list of tables for this schema.

        Returns:
            list: List of Table objects.
        """
        rows = self._connection.get_row_result("list_objects", self._name)
        rows.fetch_all()
        tables = []
        for row in rows:
            if row.get_string("type") != "TABLE":
                continue
            table = Table(self, row.get_string("name"))
            tables.append(table)
        return tables

    def get_table(self, name, check_existence=False):
        """Returns the table of the given name for this schema.

        Returns:
            mysqlx.Table: Table object.
        """
        table = Table(self, name)
        if check_existence:
            if not table.exists_in_database():
                raise Exception("table does not exist")
        return table

    def get_collection(self, name, check_existence=False):
        """Returns the collection of the given name for this schema.

        Returns:
            mysqlx.Collection: Collection object.
        """
        collection = Collection(self, name)
        if check_existence:
            if not collection.exists_in_database():
                raise Exception("collection does not exist")
        return collection

    def drop_collection(self, name):
        """Drops a collection.

        Args:
            name (str): The name of the collection to be dropped.
        """
        self._connection.execute_nonquery(
            "sql", _DROP_TABLE_QUERY.format(self._name, name), False)

    def drop_table(self, name):
        """Drops a table.

        Args:
            name (str): The name of the table to be dropped.
        """
        self._connection.execute_nonquery(
            "sql", _DROP_TABLE_QUERY.format(self._name, name), False)

    def create_collection(self, name, reuse=False):
        """Creates in the current schema a new collection with the specified
        name and retrieves an object representing the new collection created.

        Args:
            name (str): The name of the collection.
            reuse (bool): `True` to reuse an existing collection.

        Raises:
            Exception: If ``reuse`` is False and collection exists.
        """
        collection = Collection(self, name)
        if not collection.exists_in_database():
            self._connection.execute_nonquery("xplugin", "create_collection",
                                              True, self._name, name)
        elif not reuse:
            raise Exception("Collection already exists")
        return collection


class Collection(DatabaseObject):
    """Represents a collection of documents on a schema.

    Args:
        schema (mysqlx.Schema): The Schema object.
        name (str): The collection name.
    """
    def __init__(self, schema, name):
        super(Collection, self).__init__(schema, name)

    def exists_in_database(self):
        """Verifies if this object exists in the database.

        Returns:
            bool: `True` if object exists in database.
        """
        sql = _COUNT_TABLES_QUERY.format(self._schema.get_name(), self._name)
        return self._connection.execute_sql_scalar(sql) == 1

    def find(self, condition=None):
        """Retrieves documents from a collection.

        Args:
            condition (Optional[str]): The string with the filter expression of
                                       the documents to be retrieved.
        """
        return FindStatement(self, condition)

    def add(self, *values):
        """Adds a list of documents to a collection.

        Args:
            *values: The document list to be added into the collection.

        Returns:
            mysqlx.AddStatement: AddStatement object.
        """
        return AddStatement(self).add(*values)

    def remove_one(self, id):
        """Removes document by ID.

        Args:
            id (str): The document ID.

        Returns:
            mysqlx.RemoveStatement: RemoveStatement object.
        """
        return self.remove("_id = '{0}'".format(id))

    def remove(self, condition=None):
        """Removes documents based on the ``condition``.

        Args:
            condition (Optional[str]): The string with the filter expression of
                                       the documents to be removed.

        Returns:
            mysqlx.RemoveStatement: RemoveStatement object.
        """
        rs = RemoveStatement(self)
        if not condition == None:
            rs.where(condition)
        return rs

    def modify(self, condition=None):
        """Modifies documents based on the ``condition``.

        Args:
            condition (Optional[str]): The string with the filter expression of
                                       the documents to be modified.

        Returns:
            mysqlx.ModifyStatement: ModifyStatement object.
        """
        return ModifyStatement(self, condition)

    def count(self):
        """Counts the documents in the collection.

        Returns:
            int: The total of documents in the collection.
        """
        sql = _COUNT_QUERY.format(self._schema.name, self._name)
        return self._connection.execute_sql_scalar(sql)

    def create_index(self, index_name, is_unique):
        """Creates a collection index.

        Args:
            index_name (str): Index name.
            is_unique (bool): `True` if the index is unique.
        """
        return CreateCollectionIndexStatement(self, index_name, is_unique)

    def drop_index(self, index_name):
        """Drops a collection index.

        Args:
            index_name (str): Index name.
        """
        return DropCollectionIndexStatement(self, index_name)


class Table(DatabaseObject):
    """Represents a database table on a schema.

    Provides access to the table through standard INSERT/SELECT/UPDATE/DELETE
    statements.

    Args:
        schema (mysqlx.Schema): The Schema object.
        name (str): The table name.
    """
    def __init__(self, schema, name):
        super(Table, self).__init__(schema, name)

    def exists_in_database(self):
        """Verifies if this object exists in the database.

        Returns:
            bool: `True` if object exists in database.
        """
        sql = _COUNT_TABLES_QUERY.format(self._schema.name, self._name)
        return self._connection.execute_sql_scalar(sql) == 1

    def select(self, *fields):
        """Creates a new :class:`mysqlx.SelectStatement` object.

        Args:
            *fields: The fields to be retrieved.

        Returns:
            mysqlx.SelectStatement: SelectStatement object
        """
        return SelectStatement(self, *fields)

    def insert(self, *fields):
        """Creates a new :class:`mysqlx.InsertStatement` object.

        Args:
            *fields: The fields to be inserted.

        Returns:
            mysqlx.InsertStatement: InsertStatement object
        """
        return InsertStatement(self, *fields)

    def update(self):
        """Creates a new :class:`mysqlx.UpdateStatement` object.

        Args:
            *fields: The fields to update.

        Returns:
            mysqlx.UpdateStatement: UpdateStatement object
        """
        return UpdateStatement(self)

    def delete(self, condition=None):
        """Creates a new :class:`mysqlx.DeleteStatement` object.

        Args:
            condition (Optional[str]): The string with the filter expression of
                                       the rows to be deleted.

        Returns:
            mysqlx.DeleteStatement: DeleteStatement object
        """
        return DeleteStatement(self, condition)

    def count(self):
        """Counts the rows in the table.

        Returns:
            int: The total of rows in the table.
        """
        sql = _COUNT_QUERY.format(self._schema.name, self._name)
        return self._connection.execute_sql_scalar(sql)

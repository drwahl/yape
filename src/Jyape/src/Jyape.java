/**
 * @author dwahlstrom
 *
 */
import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

public class Jyape
{
	/**
	 * @param args
	 */
    public static void main(String[] args)
    	// TODO Auto-generated method stub
    {
        Properties prop = new Properties();

        try {
            prop.load(new FileInputStream("/Users/dwahlstrom/tmp/jyape.properties"));
        } catch (IOException ex) {
            ex.printStackTrace();
        }

        String dbhost = prop.getProperty("mongodb_server");
        String dbname = prop.getProperty("mongodb_db_name");
        String dbcoll = prop.getProperty("mongodb_collection_name");
        System.out.println(dbhost);
        System.out.println(dbname);
        System.out.println(dbcoll);

    }

}
